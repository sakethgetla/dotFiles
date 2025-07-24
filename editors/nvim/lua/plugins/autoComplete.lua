
-- return {
-- 	{ "hrsh7th/nvim-cmp" },
--     {
--       "mason-org/mason.nvim", opts = {}
--     },
--     {
--       "mason-org/mason-lspconfig.nvim",
--       opts = {},
--       dependencies = {
--         { "mason-org/mason.nvim", opts = {} },
--           "neovim/nvim-lspconfig",
--         },
--     },
-- }

return {
  -- "L3MON4D3/LuaSnip",
  -- 'saadparwaiz1/cmp_luasnip',
  -- "rafamadriz/friendly-snippets",
  'hrsh7th/cmp-nvim-lsp',
  'hrsh7th/cmp-buffer',
  'hrsh7th/cmp-path',


  { -- optional cmp completion source for require statements and module annotations
    "hrsh7th/nvim-cmp",
    opts = function(_, opts)
      opts.sources = opts.sources or {}
      table.insert(opts.sources, {
        name = "lazydev",
        group_index = 0, -- set group index to 0 to skip loading LuaLS completions
      })
    end,
  },

  {
    "mason-org/mason.nvim",
    opts = {
          ensure_installed = {
            "prettier",
      },
        ui = {
            icons = {
                package_installed = "✓",
                package_pending = "➜",
                package_uninstalled = "✗"
            }
        },
    }
  },



  -- 'neovim/nvim-lspconfig',
  {
    "mason-org/mason-lspconfig.nvim",
    opts = {
          -- ensure_installed = {
          --   "lua_ls",
          --   "rust_analyzer",
          --   "marksman",
          -- },
    },
    dependencies = {
        { "mason-org/mason.nvim", opts = {} },
        "neovim/nvim-lspconfig",
    },
  },


}

-- return {
-- 	-- "williamboman/mason.nvim",
--   "mason-org/mason.nvim",
-- 	dependencies = {
-- 		-- "williamboman/mason-lspconfig.nvim",
--     "mason-org/mason-lspconfig.nvim",
-- 		"WhoIsSethDaniel/mason-tool-installer.nvim",
-- 	},
-- 	config = function()
-- 		require("mason").setup()
-- 
-- 		require("mason-lspconfig").setup({
-- 			automatic_installation = true,
-- 			ensure_installed = {
-- 				"cssls",
-- 				"eslint",
-- 				"html",
-- 				"jsonls",
-- 				"ts_ls",
-- 				"pyright",
-- 				"tailwindcss",
-- 				"gopls",
-- 				"golangci_lint_ls",
-- 			},
-- 		})
-- 
-- 		require("mason-tool-installer").setup({
-- 			ensure_installed = {
-- 				"prettier",
-- 				"stylua", -- lua formatter
-- 				"isort", -- python formatter
-- 				"black", -- python formatter
-- 				"pylint",
-- 				"eslint_d",
-- 			},
-- 		})
-- 	end,
-- 	"neovim/nvim-lspconfig",
-- 	event = { "BufReadPre", "BufNewFile" },
-- 	dependencies = {
-- 		"hrsh7th/cmp-nvim-lsp",
-- 		{ "folke/neodev.nvim", opts = {} },
-- 	},
-- 	config = function()
-- 		local nvim_lsp = require("lspconfig")
-- 		local mason_lspconfig = require("mason-lspconfig")
-- 
-- 		local protocol = require("vim.lsp.protocol")
-- 
-- 		local on_attach = function(client, bufnr)
-- 			-- format on save
-- 			if client.server_capabilities.documentFormattingProvider then
-- 				vim.api.nvim_create_autocmd("BufWritePre", {
-- 					group = vim.api.nvim_create_augroup("Format", { clear = true }),
-- 					buffer = bufnr,
-- 					callback = function()
-- 						vim.lsp.buf.format()
-- 					end,
-- 				})
-- 			end
-- 		end
-- 
-- 		local capabilities = require("cmp_nvim_lsp").default_capabilities()
-- 
-- 		mason_lspconfig.setup_handlers({
-- 			function(server)
-- 				nvim_lsp[server].setup({
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["ts_ls"] = function()
-- 				nvim_lsp["ts_ls"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["cssls"] = function()
-- 				nvim_lsp["cssls"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["tailwindcss"] = function()
-- 				nvim_lsp["tailwindcss"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["html"] = function()
-- 				nvim_lsp["html"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["jsonls"] = function()
-- 				nvim_lsp["jsonls"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["eslint"] = function()
-- 				nvim_lsp["eslint"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["pyright"] = function()
-- 				nvim_lsp["pyright"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["gopls"] = function()
-- 				nvim_lsp["gopls"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 			["golangci_lint_ls"] = function()
-- 				nvim_lsp["golangci_lint_ls"].setup({
-- 					on_attach = on_attach,
-- 					capabilities = capabilities,
-- 				})
-- 			end,
-- 		})
-- 	end,
-- 	"hrsh7th/nvim-cmp",
-- 	event = "InsertEnter",
-- 	dependencies = {
-- 		"hrsh7th/cmp-buffer", -- source for text in buffer
-- 		"hrsh7th/cmp-path", -- source for file system paths
-- 		{
-- 			"L3MON4D3/LuaSnip",
-- 			version = "v2.*",
-- 			-- install jsregexp (optional!).
-- 			build = "make install_jsregexp",
-- 		},
-- 		"rafamadriz/friendly-snippets",
-- 		"onsails/lspkind.nvim", -- vs-code like pictograms
-- 	},
-- 	config = function()
-- 		local cmp = require("cmp")
-- 		local lspkind = require("lspkind")
-- 		local luasnip = require("luasnip")
-- 
-- 		require("luasnip.loaders.from_vscode").lazy_load()
-- 
-- 		cmp.setup({
-- 			snippet = {
-- 				expand = function(args)
-- 					luasnip.lsp_expand(args.body)
-- 				end,
-- 			},
-- 			mapping = cmp.mapping.preset.insert({
-- 				["<C-d>"] = cmp.mapping.scroll_docs(-4),
-- 				["<C-f>"] = cmp.mapping.scroll_docs(4),
-- 				["<C-Space>"] = cmp.mapping.complete(),
-- 				["<C-e>"] = cmp.mapping.close(),
-- 				["<CR>"] = cmp.mapping.confirm({
-- 					behavior = cmp.ConfirmBehavior.Replace,
-- 					select = true,
-- 				}),
-- 			}),
-- 			sources = cmp.config.sources({
-- 				{ name = "nvim_lsp" },
-- 				{ name = "luasnip" },
-- 				{ name = "buffer" },
-- 				{ name = "path" },
-- 			}),
-- 		})
-- 
-- 		vim.cmd([[
--       set completeopt=menuone,noinsert,noselect
--       highlight! default link CmpItemKind CmpItemMenuDefault
--     ]])
-- 	end,
-- }
