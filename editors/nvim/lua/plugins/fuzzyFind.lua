-- imported in config.lazy
return {
	"ibhagwan/fzf-lua",
	-- optional for icon support
	dependencies = { "nvim-tree/nvim-web-devicons" },
	-- or if using mini.icons/mini.nvim
	-- dependencies = { "echasnovski/mini.icons" },
	-- opts = {},
	-- keymaps = {
	-- },
	files = {
		-- no_ignore = false, -- respect ".gitignore"  by default
		no_ignore = true, -- respect ".gitignore"  by default
	},
	config = function()
		local fzf = require("fzf-lua")

		vim.keymap.set({ "n" }, "<leader><leader>", fzf.buffers, { silent = true, desc = "open buffers" })

		vim.keymap.set({ "n" }, "<leader>sf", fzf.files, { silent = true, desc = "[S]earch [F]iles" })

		vim.keymap.set({ "n" }, "<leader>sg", fzf.live_grep, { silent = true, desc = "[S]earch live [g]rep" })

		vim.keymap.set({ "n" }, "<leader>sw", fzf.grep_cword, { silent = true, desc = "[S]earch [W]ord under cursor" })

		vim.keymap.set({ "n" }, "<leader>cc", fzf.colorschemes, { silent = true, desc = "search color schemes" })
	end,
}
