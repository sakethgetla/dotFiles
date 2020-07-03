" created a sybolic link of this file in ~/.config/nvim
" can create a symbolic link with command ln -s [file]
set nocompatible              " required
filetype off                  " required

" set the runtime path to include Vundle and initialize
set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()
"
" alternatively, pass a path where Vundle should install plugins
"call vundle#begin('~/some/path/here')
"" alternatively, pass a path whe
" alternatively, pass a path whe

" let Vundle manage Vundle, required
"Plugin 'gmarik/Vundle.vim'
Plugin 'VundleVim/Vundle.vim'

" add all your plugins here (note older versions of Vundle
" used Bundle instead of Plugin)

Plugin 'tmhedberg/SimpylFold'
Plugin 'jnurmine/Zenburn'
"Plugin 'altercation/vim-colors-solarized'
Plugin 'lifepillar/vim-solarized8'
Plugin 'scrooloose/nerdtree'
Plugin 'jistr/vim-nerdtree-tabs'
"Plugin 'Lokaltog/powerline', {'rtp': 'powerline/bindings/vim/'}
Plugin 'Valloric/YouCompleteMe'
Plugin 'tpope/vim-surround'
Plugin 'artur-shaik/vim-javacomplete2'
Plugin 'w0rp/ale'
Plugin 'nathanaelkane/vim-indent-guides'
Plugin 'nvie/vim-flake8'
Plugin 'hynek/vim-python-pep8-indent'

Plugin 'jpalardy/vim-slime'
Plugin 'hanschen/vim-ipython-cell'
Plugin 'christoomey/vim-tmux-navigator'
"Plugin 'davidhalter/jedi-vim'

" ...
" All of your Plugins must be added before the following line
call vundle#end()            " required
filetype plugin indent on    " required

"Automatic reloading of .vimrc
"    " Use <TAB> to select the popup menu:
"inoremap <expr> <Tab> pumvisible() ? "\<C-n>" : "\<Tab>"
"inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"""autocmd! bufwritepost .vimrc source %

"set pastetoggle=<F2>
"set clipboard=unnamedplus
"set clipboard=unnamed
""""""""""""""""""""""""""""
"change tabs to spaces
set tabstop=4
set shiftwidth=4
set expandtab

" Mouse and backspace
set mouse=a  " on OSX press ALT and click
set bs=2     " make backspace behave like normal again

" Rebind <Leader> key
" I like to have it here becuase it is easier to reach than the default and
" it is next to ``m`` and ``n`` which I use for navigating between tabs.
let mapleader = ","

nnoremap <C-J> <C-W><C-J>
nnoremap <C-K> <C-W><C-K>
nnoremap <C-L> <C-W><C-L>
nnoremap <C-H> <C-W><C-H>

" Quicksave command


" Quick quit command
noremap <Leader>q :quit<CR>  " Quit current window
"noremap <Leader>Q :qa!<CR>   " Quit all windows
noremap <Leader>' :vs<CR>   " split window
noremap <Leader>v :split<CR>   " split window horizontally

"noremap <Leader>c :noh<CR>   " no highlight

noremap <Leader>w  :update<CR>
" does vnoremap mean visal mode and inoremap mean input mode
"vnoremap <Leader>w :update<CR>
"inoremap <Leader>w :update<CR>

" easier moving between tabs
map <Leader>n <esc>:tabprevious<CR>
map <Leader>m <esc>:tabnext<CR>

map <Leader>1 <esc>:colo solarized8_high<CR>
map <Leader>2 <esc>:colo morning<CR>

nnoremap <leader>d "_d
xnoremap <leader>d "_d

nnoremap <leader>p "0p
xnoremap <leader>p "0p

"nnoremap <leader>s <C-e>
"xnoremap <leader>s <C-e>
" map sort function to a key
"" vnoremap <Leader>s :sort<CR>


" easier moving of code blocks
" Try to go into visual mode (v), thenselect several lines of code here and
" then press ``>`` several times.
vnoremap < <gv  " better indentation
vnoremap > >gv  " better indentation

filetype off
filetype plugin indent on
syntax on


" Show whitespace
" MUST be inserted BEFORE the colorscheme command
"autocmd ColorScheme * highlight ExtraWhitespace ctermbg=red guibg=red
" au InsertLeave * match ExtraWhitespace /\s\+$/

" Enable folding
set foldmethod=indent
set foldlevel=99

" Enable folding with the spacebar
nnoremap <space> za

" what is gui_runnig ?
if has('gui_running')
  "set background=dark
  colorscheme solarized8_high
else
  colorscheme solarized8_high
endif

"call togglebg#map("<F5>")
map <C-n> :NERDTreeToggle<CR>

autocmd vimenter * set number relativenumber 

set encoding=utf-8
let g:SimpylFold_docstring_preview=1

""""""""""""""""""""""""""
" Terminal mode mappings "
""""""""""""""""""""""""""
noremap <Leader>t  :terminal<CR>
noremap <Esc> <C-\><C-n>
":tnoremap <Esc> <C-\><C-n>
"
"let g:slime_target = 'tmux'
"let g:slime_target = 'neovim'
"
"let g:ipython_cell_delimit_cells_by = 'tags'
"g:ipython_cell_tag = ['# %%', '#%%', '# <codecell>', '##'] 
"" fix paste issues in ipython
"
""let g:slime_python_ipython = 1
"------------------------------------------------------------------------------
" slime configuration 
"------------------------------------------------------------------------------
" always use tmux
let g:slime_target = 'tmux'
"let g:slime_target = 'neovim'

let g:ipython_cell_delimit_cells_by = 'tags'

let g:ipython_cell_tag = ['# %%', '#%%', '# <codecell>', '##'] 

" fix paste issues in ipython
let g:slime_python_ipython = 1

" always send text to the top-right pane in the current tmux tab without asking
let g:slime_default_config = {
            \ 'socket_name': get(split($TMUX, ','), 0),
            \ 'target_pane': '{top-right}' }
let g:slime_dont_ask_default = 1

"------------------------------------------------------------------------------
" ipython-cell configuration
"------------------------------------------------------------------------------
" Keyboard mappings. <Leader> is \ (backslash) by default

" map <Leader>s to start IPython
nnoremap <Leader>s :SlimeSend1 ipython --matplotlib<CR>

" map <Leader>r to run script
nnoremap <Leader>r :IPythonCellRun<CR>

" map <Leader>R to run script and time the execution
nnoremap <Leader>R :IPythonCellRunTime<CR>

" map <Leader>c to execute the current cell
nnoremap <Leader>c :IPythonCellExecuteCell<CR>

" map <Leader>C to execute the current cell and jump to the next cell
nnoremap <Leader>C :IPythonCellExecuteCellJump<CR>

" map <Leader>l to clear IPython screen
nnoremap <Leader>l :IPythonCellClear<CR>

" map <Leader>x to close all Matplotlib figure windows
nnoremap <Leader>x :IPythonCellClose<CR>

" map [c and ]c to jump to the previous and next cell header
nnoremap [c :IPythonCellPrevCell<CR>
nnoremap ]c :IPythonCellNextCell<CR>

" map <Leader>h to send the current line or current selection to IPython
nmap <Leader>h <Plug>SlimeLineSend
xmap <Leader>h <Plug>SlimeRegionSend

" map <Leader>p to run the previous command
nnoremap <Leader>p :IPythonCellPrevCommand<CR>

" map <Leader>Q to restart ipython
nnoremap <Leader>Q :IPythonCellRestart<CR>

" map <Leader>d to start debug mode
nnoremap <Leader>d :SlimeSend1 %debug<CR>

" map <Leader>b to exit debug mode or IPython
nnoremap <Leader>b :SlimeSend1 exit<CR>
