-- imported in config.lazy
--
return {
	{
		"tiagovla/tokyodark.nvim",
		opts = {
			-- custom options here
		},
		config = function(_, opts)
			require("tokyodark").setup(opts) -- calling setup is optional
			-- vim.cmd [[colorscheme tokyodark]]
			vim.cmd([[colorscheme evening]])
		end,
	},
}
