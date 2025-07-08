-- require('telekasten').setup({
--   home = vim.fn.expand("/mnt/data/notes"), -- Put the name of your notes directory here
-- })
--
-- -- Launch panel if nothing is typed after <leader>z
-- vim.keymap.set("n", "<leader>n", "<cmd>Telekasten panel<CR>")
--
-- -- Most used functions
-- vim.keymap.set("n", "<leader>nf", "<cmd>Telekasten find_notes<CR>")
-- vim.keymap.set("n", "<leader>ng", "<cmd>Telekasten search_notes<CR>")
-- vim.keymap.set("n", "<leader>nd", "<cmd>Telekasten goto_today<CR>")
-- vim.keymap.set("n", "<leader>nz", "<cmd>Telekasten follow_link<CR>")
-- vim.keymap.set("n", "<leader>nn", "<cmd>Telekasten new_note<CR>")
-- vim.keymap.set("n", "<leader>nc", "<cmd>Telekasten show_calendar<CR>")
-- vim.keymap.set("n", "<leader>nb", "<cmd>Telekasten show_backlinks<CR>")
-- vim.keymap.set("n", "<leader>nI", "<cmd>Telekasten insert_img_link<CR>")
-- vim.keymap.set("n", "<leader>ni", "<cmd>Telekasten insert_link<CR>")
--
-- Call insert link automatically when we start typing a link
-- vim.keymap.set("n", "[[", "<cmd>Telekasten insert_link<CR>")
--
require('obsidian').setup({
   workspaces = {
        {
          name = "notes",
          path = "/mnt/data/notes",
        },
        -- {
        --   name = "work",
        --   path = "~/vaults/work",
        -- },
      },
  -- Optional, customize how note IDs are generated given an optional title.
  ---@param title string|?
  ---@return string
  note_id_func = function(title)
    -- Create note IDs in a Zettelkasten format with a timestamp and a suffix.
    -- In this case a note with the title 'My new note' will be given an ID that looks
    -- like '1657296016-my-new-note', and therefore the file name '1657296016-my-new-note.md'
    local suffix = ""
    if title ~= nil then
      -- If title is given, transform it into valid file name.
      suffix = title
    else
      -- If title is nil, just add 4 random uppercase letters to the suffix.
      for _ = 1, 4 do
        suffix = suffix .. string.char(math.random(65, 90))
      end
    end
    return tostring(os.time()) .. "-" .. suffix
  end,
})

vim.opt.conceallevel = 1


vim.keymap.set('n', '<leader>nf', ':ObsidianQuickSwitch<CR>')
vim.keymap.set('n', '<leader>ng', ':ObsidianSearch<CR>')
vim.keymap.set('n', '<leader>no', ':ObsidianFollowLink<CR>')
vim.keymap.set('n', '<leader>nn', ':ObsidianNew<CR>')
vim.keymap.set('n', '<leader>nb', ':ObsidianBacklinks<CR>')
vim.keymap.set('n', '<leader>nI', ':ObsidianPasteImg<CR>')
-- vim.keymap.set('n', '<leader>ni', ':Obsidian<CR>')
-- vim.keymap.set('n', '<leader>nn', ':Obsidian<CR>')
