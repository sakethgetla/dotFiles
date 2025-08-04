-- require("obsidian").setup({})
-- require("obsidian").setup({
-- 	ui = { enable = false },
-- 	workspaces = {
-- 		{
-- 			name = "notes",
-- 			path = "/mnt/data/notes",
-- 		},
-- 	},
-- 	-- Optional, customize how note IDs are generated given an optional title.
-- 	---@param title string|?
-- 	---@return string
-- 	note_id_func = function(title)
-- 		local suffix = ""
-- 		if title ~= nil then
-- 			suffix = title:gsub(" ", "-"):lower()
-- 		else
-- 			error("empty note name")
-- 		end
-- 		return suffix
-- 	end,
-- 	preferred_link_style = "markdown",
-- })

-- vim.opt.conceallevel = 1

-- vim.keymap.set("n", "<leader>nf", ":ObsidianQuickSwitch<CR>")
-- vim.keymap.set("n", "<leader>ng", ":ObsidianSearch<CR>")
-- vim.keymap.set("n", "<leader>no", ":ObsidianFollowLink<CR>")
-- vim.keymap.set("n", "<leader>nn", ":ObsidianNew<CR>")
-- vim.keymap.set("n", "<leader>nb", ":ObsidianBacklinks<CR>")
-- vim.keymap.set("n", "<leader>nI", ":ObsidianPasteImg<CR>")
-- vim.keymap.set("n", "<leader>nr", ":ObsidianRename<CR>")

-- Load the checkboxes module.
-- require("markview.extras.checkboxes").setup();
-- `:Checkbox toggle`
-- `:Checkbox change`

-- require("markview.extras.editor").setup();
-- `:Editor create`

-- require("markview.extras.headings").setup();
-- `:HeadingDecrease`
--
-- require("markview.presets").tables = solid

-- require('lualine').setup()
