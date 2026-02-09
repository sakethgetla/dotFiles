-- imported in config.lazy
--
return {
	-- Catppuccin - popular theme with excellent Treesitter support
	-- Variants: catppuccin-latte (light), catppuccin-frappe, catppuccin-macchiato, catppuccin-mocha (dark)
	{
		"catppuccin/nvim",
		name = "catppuccin",
		priority = 1000,
		opts = {
			flavour = "mocha", -- latte, frappe, macchiato, mocha
			integrations = {
				treesitter = true,
				native_lsp = { enabled = true },
				gitsigns = true,
				nvimtree = true,
				neo_tree = true,
				telescope = { enabled = true },
			},
		},
	},

	-- TokyoNight - VS Code-like theme
	-- Variants: tokyonight-night, tokyonight-storm, tokyonight-day (light), tokyonight-moon
	{
		"folke/tokyonight.nvim",
		priority = 1000,
		opts = {},
	},

	-- Set the active colorscheme here
	-- Dark options: catppuccin-mocha, catppuccin-macchiato, tokyonight-night, tokyonight-storm
	-- Light options: catppuccin-latte, tokyonight-day
	{
		"tiagovla/tokyodark.nvim",
		priority = 1000,
		config = function()
			vim.cmd([[colorscheme catppuccin-mocha]])
		end,
	},
}
