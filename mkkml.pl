#!/usr/bin/perl

use strict;
use warnings;
use POSIX;

# Global variable to track broken data lines
our $broken = 0;

# Generate KML head
sub head {
    return <<'EOF';
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
EOF
}

# Generate KML styles
sub style {
    return <<'EOF';
    <Style id="hl2">
        <IconStyle>
            <scale>4.2</scale>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle_highlight.png</href>
            </Icon>
        </IconStyle>
    </Style>
    <Style id="default2">
        <IconStyle>
            <scale>4.2</scale>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>
            </Icon>
        </IconStyle>
    </Style>
    <StyleMap id="default1">
        <Pair>
            <key>normal</key>
            <styleUrl>#hl2</styleUrl>
        </Pair>
        <Pair>
            <key>highlight</key>
            <styleUrl>#default2</styleUrl>
        </Pair>
    </StyleMap>
EOF
}

# Generate KML footer
sub foot {
    return <<'EOF';
</kml>
EOF
}

# Emit a simple KML tag
sub emit {
    my ($tag, $content) = @_;
    return "<$tag>$content</$tag>\n";
}

# Convert RGB to ARGB format
sub argb {
    my ($r, $g, $b) = @_;
    return sprintf "%02x%02x%02x%02x", 255, $r * 255, $g * 255, $b * 255;
}

# Generate a rainbow color for heatmap scaling
sub rainbow {
    my ($cur, $max) = @_;
    $cur = $max if $cur > $max;
    my $h = $cur / $max * 2 / 3;  # Hue based on current/max
    my ($s, $v) = (1, 1);         # Full saturation and value
    my $i = int($h * 6);
    my $f = $h * 6 - $i;
    my $p = $v * (1 - $s);
    my $q = $v * (1 - $s * $f);
    my $t = $v * (1 - $s * (1 - $f));
    $i %= 6;

    return argb($v, $t, $p) if $i == 0;
    return argb($q, $v, $p) if $i == 1;
    return argb($p, $v, $t) if $i == 2;
    return argb($p, $q, $v) if $i == 3;
    return argb($t, $p, $v) if $i == 4;
    return argb($v, $p, $q) if $i == 5;

    die "Unexpected hue index: $i";
}

# Quantize a value based on a given step
sub quant {
    my ($val, $step) = @_;
    return $val < 0 ? int($val / $step - 1) * $step : int($val / $step) * $step;
}

# Add a point to the dataset
sub add_pt {
    my ($ref, $x, $y, $h, $val) = @_;
    push @{$ref}, [$x, $y, $h, $val];
}

# Parse a single line of input data
sub read_line {
    my ($data, $line) = @_;

    if ($line =~ /^IRA: (\S+) ([\d.]+) \d+\s+(\d+)%\s+[0-9.|-]+([0-9.]+).* sat:(\d+) beam:(\d+) .*pos=([+-][0-9.]+)\/([+-][0-9.]+). alt=(-?\d+)/) {
        my ($fn, $t, $conf, $str, $sat, $beam, $x, $y, $h) = ($1, $2, $3, $4, $5, $6, $7, $8, $9);

        # Convert time from filename if available
        if ($fn =~ /-(\d{10})-/) {
            $t = $1 + $t / 1000;
        } else {
            $t = $t / 1000;
        }

        # Determine direction
        my $dir;
        if ($h > 600 && $h < 900) {
            $dir = "up";
        } elsif ($h > -100 && $h < 100) {
            $dir = "down";
        } else {
            $broken++;
            return;  # Ignore invalid data
        }

        $sat = sprintf "%03d", $sat;
        $h *= 1000;
        $data->{$dir} //= [];
        add_pt($data->{$dir}, $y, $x, $h, $str);

        my $track_key = $dir eq "down" ? "track_down" : "track_up";
        $data->{$track_key}{$sat}{$beam} //= [];
        add_pt($data->{$track_key}{$sat}{$beam}, $y, $x, $h, $t);
    } else {
        warn "Couldn't parse line: $line\n";
    }
}

# Read all data from STDIN
sub read_data {
    my $data = shift;
    while (<STDIN>) {
        chomp;
        read_line($data, $_);
    }
}

# Main logic
sub main {
    my $mode = shift @ARGV or die "Usage: $0 {heatmap|beams|tracks}\n";

    my $data = {};
    read_data($data);

    warn "Ignored $broken lines with incorrect altitude\n" if $broken > 0;

    print head(), "<Folder>\n", style();

    if ($mode eq "tracks") {
        do_tracks($data->{track_up});
    } elsif ($mode eq "beams") {
        do_beams($data->{track_down});
    } elsif ($mode eq "heatmap") {
        my $deg = shift || 0.5;
        do_heatmap($data->{down}, "Down", $deg);
        do_heatmap($data->{up}, "Up", $deg);
    }

    print "</Folder>\n", foot();
}

main();