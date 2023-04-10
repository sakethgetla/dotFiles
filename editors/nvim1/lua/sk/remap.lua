vim.g.mapleader = " "
vim.keymap.set("n", "<leader>pv", vim.cmd.Ex)
vim.keymap.set("n", "<leader>ww", vim.cmd.w)
vim.keymap.set("n", "<leader>wq", vim.cmd.q)

vim.keymap.set("n", "<leader>mf", vim.lsp.buf.format)


vim.keymap.set("n", "<leader>wh", "<C-w><C-h>")
vim.keymap.set("n", "<leader>wl", "<C-w><C-l>")
vim.keymap.set("n", "<leader>wj", "<C-w><C-j>")
vim.keymap.set("n", "<leader>wk", "<C-w><C-k>")

vim.keymap.set("n", "<leader>fw", "<C-w><C-q>")

-- copy to clipboard
vim.keymap.set({"v", "n" }, "<leader>y", [["+y]])
vim.keymap.set( "n", "<leader>Y", [["+Y]])
