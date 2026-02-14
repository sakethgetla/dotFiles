return {
	{
		"williamboman/mason.nvim",
		config = function()
			require("mason").setup()
		end,
	},
	{
		"williamboman/mason-lspconfig.nvim",
		dependencies = {
			"williamboman/mason.nvim",
			"neovim/nvim-lspconfig",
			"hrsh7th/cmp-nvim-lsp",
		},
		config = function()
			require("mason-lspconfig").setup({
				automatic_installation = true,
				ensure_installed = {
					"cssls",
					"html",
					"jsonls",
					"ts_ls",
					"pyright",
					"tailwindcss",
					"vue_ls",
				},
			})

			-- global capabilities for all LSP servers
			vim.lsp.config("*", {
				capabilities = require("cmp_nvim_lsp").default_capabilities(),
			})

			local vue_ls_path = vim.fn.stdpath("data") .. "/mason/packages/vue-language-server"

			-- ts_ls with vue typescript plugin
			vim.lsp.config("ts_ls", {
				init_options = {
					plugins = {
						{
							name = "@vue/typescript-plugin",
							location = vue_ls_path .. "/node_modules/@vue/typescript-plugin",
							languages = { "javascript", "typescript", "vue" },
						},
					},
				},
				filetypes = { "typescript", "javascript", "javascriptreact", "typescriptreact", "vue" },
			})

			-- vue_ls with tsdk path
			vim.lsp.config("vue_ls", {
				init_options = {
					typescript = {
						tsdk = vue_ls_path .. "/node_modules/typescript/lib",
					},
				},
			})

			vim.lsp.enable({
				"cssls",
				"html",
				"jsonls",
				"ts_ls",
				"pyright",
				"tailwindcss",
				"vue_ls",
			})
		end,
	},
	{
		"WhoIsSethDaniel/mason-tool-installer.nvim",
		dependencies = { "williamboman/mason.nvim" },
		config = function()
			require("mason-tool-installer").setup({
				ensure_installed = {
					"prettier",
					"stylua",
					"black",
				},
			})
		end,
	},
	{ "folke/neodev.nvim", opts = {} },
}
