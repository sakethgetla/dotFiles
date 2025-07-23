
return { 
  -- {
  --   "3rd/image.nvim",
  -- } 
  -- {
  --   "3rd/image.nvim",
  --   event = "VeryLazy",
  --   dependencies = {
  --     {
  --       "nvim-treesitter/nvim-treesitter",
  --       -- build = ":TSUpdate",
  --       -- config = function()
  --       --   require("nvim-treesitter.configs").setup({
  --       --     ensure_installed = { "markdown" },
  --       --     highlight = { enable = true },
  --       --   })
  --       -- end,
  --     },
  --   },
  --   opts = {
  --     backend = "kitty",
  --     integrations = {
  --       markdown = {
  --         enabled = true,
  --         clear_in_insert_mode = false,
  --         download_remote_images = true,
  --         only_render_image_at_cursor = false,
  --         filetypes = { "markdown", "vimwiki" }, -- markdown extensions (ie. quarto) can go here
  --       },
  --       neorg = {
  --         enabled = true,
  --         clear_in_insert_mode = false,
  --         download_remote_images = true,
  --         only_render_image_at_cursor = false,
  --         filetypes = { "norg" },
  --       },
  --     },
  --     max_width = nil,
  --     max_height = nil,
  --     max_width_window_percentage = nil,
  --     max_height_window_percentage = 50,
  --     kitty_method = "normal",
  --   },
  -- },
  {
    "folke/snacks.nvim",
    -- priority = 1000,
    -- lazy = false,
    ---@type snacks.Config
    opts = {
      -- your configuration comes here
      -- or leave it empty to use the default settings
      -- refer to the configuration section below

    image = {
      enable = true,
        doc = {
          inline = true,
          float = true,
          max_width = 60,
          max_height = 30,
    },
    },
      -- bigfile = { enabled = true },
      -- dashboard = { enabled = true },
      -- explorer = { enabled = true },
      -- indent = { enabled = true },
      -- input = { enabled = true },
      -- picker = { enabled = true },
      -- notifier = { enabled = true },
      -- quickfile = { enabled = true },
      -- scope = { enabled = true },
      -- scroll = { enabled = true },
      -- statuscolumn = { enabled = true },
      -- words = { enabled = true },
    },
  }
}

