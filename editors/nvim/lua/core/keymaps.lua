vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

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

-- vim.cmd [[ set noswapfile ]]

-- --Line numbers_
vim.wo.relativenumber = true
vim.wo.number = true

vim.keymap.set('n', '<leader>ww', vim.cmd.write)
vim.keymap.set('n', '<leader>qa', vim.cmd.quitall)
vim.keymap.set('n', '<leader>qq', vim.cmd.quit)

-- local api = require "nvim-tree.api"
-- vim.keymap.set('n', '<leader>tt', nvim-tree-api.tree.toggle)
-- vim.keymap.set('n', '<leader>tt', api.tree.toggle)
