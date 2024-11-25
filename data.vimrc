" Basic Settings
set nowrap
set showcmd
set nosol
set ve=all

" Highlighting
hi ColorColumn ctermbg=lightgreen
set cursorline cursorcolumn
hi CursorColumn ctermfg=red

" Keyword Settings
set isk=@,48-57,124,192-255

" Character Mapping for 0 and _
nnoremap ,0 mx:%s/0/_/g:nohl`x
nnoremap ,1 mx:%s/_/0/g:nohl`x

" Color Column Intervals
nnoremap ,7 :let &l:colorcolumn = join(range(1,999,16),',')<CR>
nnoremap ,8 :let &l:colorcolumn = join(range(1,999,32),',')<CR>
nnoremap ,9 :let &l:colorcolumn = join(range(93,999,33),',')<CR>

" Clean and Process Text
nnoremap ,p :%s/ //g | %s/^\[//g | %s/]$// | %s/0/_/g<CR> | :%!.uniq -c 1G/^[_|]*1[_|]*\|<CR>

" Sorting Function
function! DoSort() range abort
  let col = col(".")
  execute "%!sort -t '\x01' -k 1.".col
endfunction
nnoremap ,s mx:call DoSort()<CR>`x

" Column Highlighting Functions
function! DoCol() range abort
  let col = col(".")
  let &l:colorcolumn = col
  echo "Marking column:" col
endfunction

function! DoVisCol() range abort
  let [lnum1, col1] = getpos("'<")[1:2]
  let [lnum2, col2] = getpos("'>")[1:2]
  let &l:colorcolumn = join(range(col1, 999, col2 - col1 + 1), ',')
  echo "Start at column" col1 ", repeating every" (col2 - col1 + 1)
endfunction

vnoremap ,c mx:call DoVisCol()<CR>`x
nnoremap ,c :call DoCol()<CR>

" Paste Without Moving Cursor
function! Pcol() abort
  let l:col = virtcol('.')
  execute 'normal! p'
  call cursor('.', l:col)
endfunction
function! Pcolup() abort
  let l:col = virtcol('.')
  execute 'normal! P'
  call cursor('.', l:col)
endfunction

nnoremap <silent> p :call Pcol()<CR>
nnoremap <silent> P :call Pcolup()<CR>

" Stay in Column When Creating a New Line
nnoremap <silent> o mxo<Esc>`xji