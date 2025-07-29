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

-- return {
-- ~/nvim/lua/slydragonn/plugins/cmp.lua

return {
	{
		"hrsh7th/nvim-cmp",
		event = "InsertEnter",
		dependencies = {
			"hrsh7th/cmp-buffer", -- source for text in buffer
			"hrsh7th/cmp-path", -- source for file system paths
			{
				"L3MON4D3/LuaSnip",
				version = "v2.*",
				-- install jsregexp (optional!).
				build = "make install_jsregexp",
			},
			"rafamadriz/friendly-snippets",
			-- "onsails/lspkind.nvim", -- vs-code like pictograms
		},
		config = function()
			local cmp = require("cmp")
			-- local lspkind = require("lspkind")
			local luasnip = require("luasnip")

			require("luasnip.loaders.from_vscode").lazy_load()

			cmp.setup({
				snippet = {
					expand = function(args)
						luasnip.lsp_expand(args.body)
					end,
				},
				mapping = cmp.mapping.preset.insert({
					["<Tab>"] = cmp.mapping(function(fallback)
						if cmp.visible() then
							cmp.select_next_item()
						else
							fallback()
						end
					end, { "i", "s" }),
					["<S-Tab>"] = cmp.mapping(function(fallback)
						if cmp.visible() then
							cmp.select_prev_item()
						else
							fallback()
						end
					end, { "i", "s" }),
					["<C-d>"] = cmp.mapping.scroll_docs(-4),
					["<C-f>"] = cmp.mapping.scroll_docs(4),
					["<C-Space>"] = cmp.mapping.complete(),
					["<C-e>"] = cmp.mapping.close(),
					["<CR>"] = cmp.mapping.confirm({
						behavior = cmp.ConfirmBehavior.Replace,
						select = true,
					}),
				}),
				sources = cmp.config.sources({
					{ name = "nvim_lsp" },
					{ name = "luasnip" },
					{ name = "buffer" },
					{ name = "path" },
				}),
			})

			vim.cmd([[
      set completeopt=menuone,noinsert,noselect
      highlight! default link CmpItemKind CmpItemMenuDefault
    ]])
		end,
	},
	--
	--
	-- -- "L3MON4D3/LuaSnip",
	-- -- 'saadparwaiz1/cmp_luasnip',
	-- -- "rafamadriz/friendly-snippets",
	-- 'hrsh7th/cmp-nvim-lsp',
	-- 'hrsh7th/cmp-buffer',
	-- 'hrsh7th/cmp-path',
	--
	--
	--
	-- { -- optional cmp completion source for require statements and module annotations
	--   "hrsh7th/nvim-cmp",
	--   opts = function(_, opts)
	--     opts.sources = opts.sources or {}
	--     table.insert(opts.sources, {
	--       name = "lazydev",
	--       group_index = 0, -- set group index to 0 to skip loading LuaLS completions
	--     })
	--   end,
	-- },
	--

	-- {
	--   "mason-org/mason.nvim",
	--   opts = {
	--     ensure_installed = {
	--       "prettier",
	--     },
	--     ui = {
	--       icons = {
	--         package_installed = "✓",
	--         package_pending = "➜",
	--         package_uninstalled = "✗"
	--       }
	--     },
	--   }
	-- },

	-- -- 'neovim/nvim-lspconfig',
	-- {
	--   "mason-org/mason-lspconfig.nvim",
	--   opts = {
	--     -- ensure_installed = {
	--     --   "lua_ls",
	--     --   "rust_analyzer",
	--     --   "marksman",
	--     -- },
	--   },
	--   dependencies = {
	--     { "mason-org/mason.nvim", opts = {} },
	--     "neovim/nvim-lspconfig",
	--   },
	-- },
}
