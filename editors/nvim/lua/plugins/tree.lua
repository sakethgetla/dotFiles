-- disable netrw at the very start of your init.lua
vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

-- optionally enable 24-bit colour
vim.opt.termguicolors = true

return {
  "nvim-neo-tree/neo-tree.nvim",
  branch = "v3.x",
    -- keys = {
    --   { "<leader>tt", "<cmd>Neotree toggle<cr>", desc = "NeoTree" },
    -- },
  dependencies = {
    "nvim-lua/plenary.nvim",
    "nvim-tree/nvim-web-devicons", -- not strictly required, but recommended
    "MunifTanjim/nui.nvim",
    -- Optional image support for file preview: See `# Preview Mode` for more information.
    -- {"3rd/image.nvim", opts = {}},
    -- OR use snacks.nvim's image module:
    -- "folke/snacks.nvim",
  },
  lazy = false, -- neo-tree will lazily load itself
  ---@module "neo-tree"
  ---@type neotree.Config?
  opts = {
    window = {
      mappings = {
        ["y"] = function(state)
          local node = state.tree:get_node()
          local filepath = node:get_id()
          local filename = node.name
          local modify = vim.fn.fnamemodify

          local results = {
            filepath,
            modify(filepath, ":."),
            filename,
          }

          vim.ui.select(results, { prompt = "Choose to copy:" }, function(choice)
            if choice then
              vim.fn.setreg("+", choice)
              vim.notify("Copied: " .. choice)
            end
          end)
        end,
      },
    },
  },
}
