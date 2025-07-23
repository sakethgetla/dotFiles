vim.keymap.set('n', '<leader>ww', vim.cmd.write)
vim.keymap.set('n', '<leader>qa', vim.cmd.quitall)
vim.keymap.set('n', '<leader>qq', vim.cmd.quit)

vim.keymap.set('n', '<leader>r', ':nohlsearch<CR>')

vim.keymap.set("n", "<leader>h", "<C-w><C-h>")
vim.keymap.set("n", "<leader>l", "<C-w><C-l>")
vim.keymap.set("n", "<leader>j", "<C-w><C-j>")
vim.keymap.set("n", "<leader>k", "<C-w><C-k>")

-- local api = require "nvim-tree.api"
-- vim.keymap.set('n', '<leader>tt', nvim-tree-api.tree.toggle)
-- vim.keymap.set('n', '<leader>tt', api.tree.toggle)

-- copy to clipboard, requirments xclip
vim.keymap.set({ "v", "n" }, "<leader>y", [["+y]])
vim.keymap.set("n", "<leader>Y", [["+Y]])


vim.keymap.set("v", "J", ":m '>+1<CR>gv=gv")
vim.keymap.set("v", "K", ":m '<-2<CR>gv=gv")

-- move highlight to void register, and paste
vim.keymap.set("x", "<leader>p", [["_dP]])

-- delete to void register
vim.keymap.set({ "n", "v" }, "<leader>d", [["_d]])



-- vim.keymap.set('n', '<leader>gd', vim.lsp.buf.definition)
vim.keymap.set('n', 'gd', vim.lsp.buf.definition)
