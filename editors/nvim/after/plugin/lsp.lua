-- Learn the keybindings, see :help lsp-zero-keybindings
-- Learn to configure LSP servers, see :help lsp-zero-api-showcase
local lsp = require('lsp-zero')
lsp.preset('recommended')
lsp.ensure_installed({'tsserver', 'eslint'})

-- -- (Optional) Configure lua language server for neovim
-- lsp.nvim_workspace()

-- lsp.on_attach(function(client, bufnr)
-- 	local opts = {buffer = bufnr, remap = false}
-- 	vim.keymap.set("n", "gd", function() vim.lsp.buf.definition() end, opts)
-- end)

lsp.setup()
