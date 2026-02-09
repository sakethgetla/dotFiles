return {
	-- {
	-- 	"nvim-treesitter/nvim-treesitter",
	-- 	build = ":TSUpdate",
	-- },

	{
		"nvim-treesitter/nvim-treesitter",
		build = ":TSUpdate",
		main = "nvim-treesitter.configs",
		opts = {
			ensure_installed = {
				"c",
				"lua",
				"vim",
				"vimdoc",
				"query",
				"markdown",
				"markdown_inline",
				"python",
				"html",
				"latex",
				"typst",
				"yaml",
				"bash",
			},
			sync_install = false,
			auto_install = true,
			ignore_install = { "javascript" },
			highlight = {
				enable = true,
				disable = function(lang, buf)
					local disabled_langs = { "c", "rust" }
					if vim.tbl_contains(disabled_langs, lang) then
						return true
					end
					local max_filesize = 100 * 1024 -- 100 KB
					local ok, stats = pcall(vim.loop.fs_stat, vim.api.nvim_buf_get_name(buf))
					if ok and stats and stats.size > max_filesize then
						return true
					end
				end,
				additional_vim_regex_highlighting = false,
			},
		},
	},
}
