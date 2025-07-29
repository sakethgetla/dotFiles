return {
	{
		"williamboman/mason.nvim",
		dependencies = {
			"williamboman/mason-lspconfig.nvim",
			"WhoIsSethDaniel/mason-tool-installer.nvim",
		},
		config = function()
			require("mason").setup()

			require("mason-lspconfig").setup({
				automatic_installation = true,
				ensure_installed = {
					"cssls",
					"eslint",
					"html",
					"jsonls",
					-- "tsserver",
					"pyright",
					-- "jedi_language_server",
					"tailwindcss",
				},
			})

			require("mason-tool-installer").setup({
				ensure_installed = {
					"prettier",
					"stylua", -- lua formatter
					-- "isort", -- python formatter
					"black", -- python formatter
					"pylint",
					"eslint_d",
				},
			})
		end,
	},
	-- {
	-- 	"neovim/nvim-lspconfig",
	--
	-- },
	{
		"neovim/nvim-lspconfig",
		dependencies = {
			"hrsh7th/cmp-nvim-lsp",
			{ "folke/neodev.nvim", opts = {} },
		},
	},
	-- {
	-- 	"neovim/nvim-lspconfig",
	-- 	-- event = { "BufReadPre", "BufNewFile" },
	-- 	dependencies = {
	-- 		"hrsh7th/cmp-nvim-lsp",
	-- 		{ "folke/neodev.nvim", opts = {} },
	-- 	},
	-- 	-- config = function()
	-- 	-- 	local nvim_lsp = require("lspconfig")
	-- 	-- 	local mason_lspconfig = require("mason-lspconfig")

	-- 	-- 	local protocol = require("vim.lsp.protocol")

	-- 	-- 	local on_attach = function(client, bufnr)
	-- 	-- 		-- format on save
	-- 	-- 		if client.server_capabilities.documentFormattingProvider then
	-- 	-- 			vim.api.nvim_create_autocmd("BufWritePre", {
	-- 	-- 				group = vim.api.nvim_create_augroup("Format", { clear = true }),
	-- 	-- 				buffer = bufnr,
	-- 	-- 				callback = function()
	-- 	-- 					vim.lsp.buf.format()
	-- 	-- 				end,
	-- 	-- 			})
	-- 	-- 		end
	-- 	-- 	end

	-- 	-- 	local capabilities = require("cmp_nvim_lsp").default_capabilities()

	-- 	-- 	-- mason_lspconfig.setup_handlers({
	-- 	-- 	-- 	function(server)
	-- 	-- 	-- 		nvim_lsp[server].setup({
	-- 	-- 	-- 			capabilities = capabilities,
	-- 	-- 	-- 		})
	-- 	-- 	-- 	end,
	-- 	-- 	-- 	-- ["tsserver"] = function()
	-- 	-- 	-- 	-- 	nvim_lsp["tsserver"].setup({
	-- 	-- 	-- 	-- 		on_attach = on_attach,
	-- 	-- 	-- 	-- 		capabilities = capabilities,
	-- 	-- 	-- 	-- 	})
	-- 	-- 	-- 	-- end,
	-- 	-- 	-- 	["cssls"] = function()
	-- 	-- 	-- 		nvim_lsp["cssls"].setup({
	-- 	-- 	-- 			on_attach = on_attach,
	-- 	-- 	-- 			capabilities = capabilities,
	-- 	-- 	-- 		})
	-- 	-- 	-- 	end,
	-- 	-- 	-- 	["tailwindcss"] = function()
	-- 	-- 	-- 		nvim_lsp["tailwindcss"].setup({
	-- 	-- 	-- 			on_attach = on_attach,
	-- 	-- 	-- 			capabilities = capabilities,
	-- 	-- 	-- 		})
	-- 	-- 	-- 	end,
	-- 	-- 	-- 	["html"] = function()
	-- 	-- 	-- 		nvim_lsp["html"].setup({
	-- 	-- 	-- 			on_attach = on_attach,
	-- 	-- 	-- 			capabilities = capabilities,
	-- 	-- 	-- 		})
	-- 	-- 	-- 	end,
	-- 	-- 	-- 	["jsonls"] = function()
	-- 	-- 	-- 		nvim_lsp["jsonls"].setup({
	-- 	-- 	-- 			on_attach = on_attach,
	-- 	-- 	-- 			capabilities = capabilities,
	-- 	-- 	-- 		})
	-- 	-- 	-- 	end,
	-- 	-- 	-- 	["eslint"] = function()
	-- 	-- 	-- 		nvim_lsp["eslint"].setup({
	-- 	-- 	-- 			on_attach = on_attach,
	-- 	-- 	-- 			capabilities = capabilities,
	-- 	-- 	-- 		})
	-- 	-- 	-- 	end,
	-- 	-- 	-- 	["pyright"] = function()
	-- 	-- 	-- 		nvim_lsp["pyright"].setup({
	-- 	-- 	-- 			on_attach = on_attach,
	-- 	-- 	-- 			capabilities = capabilities,
	-- 	-- 	-- 		})
	-- 	-- 	-- 	end,
	-- 	-- 	-- })
	-- 	-- end,
	-- },
}
