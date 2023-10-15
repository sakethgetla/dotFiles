require("mason").setup()
require("mason-lspconfig").setup {
  ensure_installed = { "lua_ls", "tsserver", "pyright", "jsonls", "dockerls", "html", "grammarly", "awk_ls", "sqls",
    "yamlls", "prismals", "bashls" },
}

local lspConfig = require("lspconfig")

-- local onAttach = function(_, _)
--   -- Buffer local mappings.
--   -- See `:help vim.lsp.*` for documentation on any of the below functions
--   local opts = { buffer = ev.buf }
--   vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
--   vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
--   vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
--   vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
--   -- vim.keymap.set('n', '<leader>wa', vim.lsp.buf.add_workspace_folder, opts)
--   -- vim.keymap.set('n', '<leader>wr', vim.lsp.buf.remove_workspace_folder, opts)
--   -- vim.keymap.set('n', '<leader>wl', function()
--   --   print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
--   -- end, opts)
--   vim.keymap.set('n', '<leader>D', vim.lsp.buf.type_definition, opts)
--   -- vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts)
--   -- vim.keymap.set({ 'n', 'v' }, '<leader>ca', vim.lsp.buf.code_action, opts)
--   vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
--   -- vim.keymap.set('n', '<leader>fm', function()
--   --   vim.lsp.buf.format { async = true }
--   -- end, opts)
--   -- vim.keymap.set('n', '<leader>fm', vim.lsp.buf.format, opts)
--   vim.keymap.set('n', '<space>fm', vim.lsp.buf.format, opts)
-- end




-- lspConfig.lua_ls.setup {
--   -- on_attach = onAttach
-- }
-- lspConfig.tsserver.setup {}

-- nvim-cmp supports additional completion capabilities, so broadcast that to servers
-- local capabilities = vim.lsp.protocol.make_client_capabilities()
-- capabilities = require('cmp_nvim_lsp').default_capabilities(capabilities)

-- Enable some language servers with the additional completion capabilities offered by coq_nvim
local servers = { 'tsserver', "lua_ls" }

-- local coq = require('coq')

local capabilities = require('cmp_nvim_lsp').default_capabilities()
for _, lsp in ipairs(servers) do
  lspConfig[lsp].setup({

      capabilities = capabilities,
  })

  -- lspConfig[lsp].setup(coq.lsp_ensure_capabilities({
  --     capabilities = capabilities,
  --   -- on_attach = my_custom_on_attach,
  -- }))
end

-- local lsp_defaults = lspConfig.util.default_config
-- 
-- lsp_defaults.capabilities = vim.tbl_deep_extend(
--   'force',
--   lsp_defaults.capabilities,
--   -- require('coq').lsp_ensure_capabilities({})
--   -- require('coq').default_capabilities()
-- )


-- coq.Now()

-- Use LspAttach autocommand to only map the following keys
-- after the language server attaches to the current buffer
vim.api.nvim_create_autocmd('LspAttach', {
  group = vim.api.nvim_create_augroup('UserLspConfig', {}),
  callback = function(ev)
    -- Enable completion triggered by <c-x><c-o>
    vim.bo[ev.buf].omnifunc = 'v:lua.vim.lsp.omnifunc'

    -- Buffer local mappings.
    -- See `:help vim.lsp.*` for documentation on any of the below functions
    local opts = { buffer = ev.buf }
    vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
    vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
    vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
    vim.keymap.set('n', '<C-k>', vim.lsp.buf.signature_help, opts)

    -- vim.keymap.set('n', '<space>wa', vim.lsp.buf.add_workspace_folder, opts)
    -- vim.keymap.set('n', '<space>wr', vim.lsp.buf.remove_workspace_folder, opts)
    -- vim.keymap.set('n', '<space>wl', function()
    --   print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
    -- end, opts)


    vim.keymap.set('n', '<space>D', vim.lsp.buf.type_definition, opts)
    -- vim.keymap.set('n', '<space>rn', vim.lsp.buf.rename, opts)
    vim.keymap.set({ 'n', 'v' }, '<space>ca', vim.lsp.buf.code_action, opts)
    vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
    vim.keymap.set('n', '<space>fm', function()
      vim.lsp.buf.format { async = true }
    end, opts)
    -- vim.keymap.set('n', '<space>fm', vim.lsp.buf.format, opts)
    -- vim.keymap.set('n', '<bs>', null, opts)
  end,
})
