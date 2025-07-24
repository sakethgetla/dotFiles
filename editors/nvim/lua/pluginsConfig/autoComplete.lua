-- require("mason").setup({})

-- require("mason-lspconfig").setup ( {
--     ensure_installed = {
--       "lua_ls",
--       "rust_analyzer",
--       "marksman",
--       "pylsp",
--       -- "autopep8",
--     },
-- } )


-- local cmp = require('cmp')
-- local luasnip = require 'luasnip'

-- require("luasnip.loaders.from_vscode").lazy_load()

-- cmp.setup({
-- 
--   mapping = cmp.mapping.preset.insert({
--     ['<Tab>'] = cmp.mapping(function(fallback)
--       if cmp.visible() then
--         cmp.select_next_item()
--       else
--         fallback()
--       end
--     end, { 'i', 's' }),
--     ['<S-Tab>'] = cmp.mapping(function(fallback)
--       if cmp.visible() then
--         cmp.select_prev_item()
--       else
--         fallback()
--       end
--     end, { 'i', 's' }),
--     ['<C-b>'] = cmp.mapping.scroll_docs(-4),
--     ['<C-f>'] = cmp.mapping.scroll_docs(4),
--     ['<C-Space>'] = cmp.mapping.complete(),
--     ['<C-e>'] = cmp.mapping.abort(),
--     ['<CR>'] = cmp.mapping.confirm({ select = true }), -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
--   }),
--   sources = cmp.config.sources({
--     { name = 'nvim_lsp' },
--     -- { name = 'vsnip' }, -- For vsnip users.
--     -- { name = 'luasnip' }, -- For luasnip users.
--     -- { name = 'ultisnips' }, -- For ultisnips users.
--     -- { name = 'snippy' }, -- For snippy users.
--   }, {
--     { name = 'buffer' },
--   })
-- })



local cmp = require('cmp')
cmp.setup({
  -- snippet = {
  --   expand = function(args)
  --     luasnip.lsp_expand(args.body)
  --   end,
  -- },
  mapping = cmp.mapping.preset.insert({

    -- ['<Tab>'] = cmp.mapping(cmp.select_next_item()),
    ['<Tab>'] = cmp.mapping(function(fallback)
      if cmp.visible() then
        cmp.select_next_item()
      else
        fallback()
      end
    end, { 'i', 's' }),
    ['<S-Tab>'] = cmp.mapping(function(fallback)
      if cmp.visible() then
        cmp.select_prev_item()
      else
        fallback()
      end
    end, { 'i', 's' }),
    -- ["<C-k>"] = cmp.mapping.select_prev_item(), -- previous suggestion
    -- ["<C-j>"] = cmp.mapping.select_next_item(), -- next suggestion
    -- ["<C-b>"] = cmp.mapping.scroll_docs(-4),
    -- ["<C-f>"] = cmp.mapping.scroll_docs(4),
    -- ["<C-Space>"] = cmp.mapping.complete(), -- show completion suggestions
    -- ["<C-e>"] = cmp.mapping.abort(), -- close completion window
    ["<CR>"] = cmp.mapping.confirm({ select = false }),
  }),
  -- sources for autocompletion
  sources = cmp.config.sources({
    { name = "nvim_lsp" }, -- LSP
    -- { name = "luasnip" }, -- snippets
    { name = "buffer" }, -- text within the current buffer
    { name = "path" }, -- file system paths
  }),
})

vim.keymap.set('n', '<leader>gd', vim.lsp.buf.definition)


-- require("mason-lspconfig").setup {
--     ensure_installed = {
--             "lua_ls",
--             "rust_analyzer",
--                  "marksman",
--             -- "eslint",
--             -- "prettier",
--     },
-- }

