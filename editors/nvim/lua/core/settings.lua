
vim.opt.backspace = '2'
vim.opt.showcmd = true

-- vim.opt.laststatus = 2
-- vim.opt.autowrite = true
-- vim.opt.cursorline = true
-- vim.opt.autoread = true

-- use spaces for tabs and whatnot
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.shiftround = true
vim.opt.expandtab = true

-- Save undo history
vim.o.undofile = true

-- search
vim.opt.hlsearch = true
vim.opt.incsearch = true

-- vim.cmd [[ set noswapfile ]]

-- --Line numbers_
vim.wo.relativenumber = true
vim.wo.number = true


-- Case insensitive searching UNLESS /C or capital in search
vim.o.ignorecase = true
vim.o.smartcase = true

vim.opt.termguicolors = true

-- [[ Highlight on yank ]]
-- See `:help vim.highlight.on_yank()`
local highlight_group = vim.api.nvim_create_augroup('YankHighlight', { clear = true })
vim.api.nvim_create_autocmd('TextYankPost', {
  callback = function()
    vim.highlight.on_yank()
  end,
  group = highlight_group,
  pattern = '*',
})

-- cusor cant go lower than 8 lines from the bottom and top
vim.opt.scrolloff = 8
vim.opt.signcolumn = "yes"
vim.opt.isfname:append("@-@")


-- -- column
-- vim.opt.colorcolumn = "80"

-- line width
vim.opt.textwidth = 80


vim.opt.updatetime = 50


-- Keep signcolumn on by default
vim.wo.signcolumn = 'yes'

-- -- fold
-- vim.wo.foldmethod = 'expr'
-- vim.wo.foldexpr = 'v:lua.vim.treesitter.foldexpr()'

-- spell
vim.cmd [[autocmd FileType * setlocal spell spelllang=en_us]] 
-- better to add "autocmd FileType *" 
-- because it triggers command every time a new files is opened 
-- unlike the following command
   -- vim.cmd ':setlocal spell spelllang=en_us'


-- vim.g.lazyvim_prettier_needs_config = false

vim.opt.conceallevel = 1
