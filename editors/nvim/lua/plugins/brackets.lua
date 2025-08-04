return {
	"windwp/nvim-autopairs",
	event = "InsertEnter",
	-- config = true,
	config = function()
		require("nvim-autopairs").setup({})
	end,
	opts = {},
	-- use opts = {} for passing setup options
	-- this is equivalent to setup({}) function
}
