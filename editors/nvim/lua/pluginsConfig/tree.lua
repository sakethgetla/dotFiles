vim.keymap.set("n", "<leader>tt", function()
	if vim.bo.filetype == "neo-tree" then
		vim.cmd("Neotree close")
	else
		vim.cmd("Neotree reveal")
	end
end)
