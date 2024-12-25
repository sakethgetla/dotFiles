local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", -- latest stable release
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

local plugins = {
  -- 'dracula/vim',
  'nvim-tree/nvim-tree.lua',
  'nvim-tree/nvim-web-devicons',
  'marko-cerovac/material.nvim',
  'nvim-lualine/lualine.nvim',

  -- 'ts_context_commentstring',
  {
    'nvim-treesitter/nvim-treesitter',
    dependencies = {
      'JoosepAlviste/nvim-ts-context-commentstring',

      'nvim-treesitter/nvim-treesitter-textobjects',
    },
  },

  -- -- Useful plugin to show you pending keybinds.
  -- { 'folke/which-key.nvim', opts = {} },

  -- {
  --   'nvim-telescope/telescope.nvim',
  --   branch = '0.1.x',
  --   dependencies = { 'nvim-lua/plenary.nvim' }
  -- },

  -- Fuzzy Finder (files, lsp, etc)
  {
    'nvim-telescope/telescope.nvim',
    branch = '0.1.x',
    dependencies = {
      'nvim-lua/plenary.nvim',
      -- Fuzzy Finder Algorithm which requires local dependencies to be built.
      -- Only load if `make` is available. Make sure you have the system
      -- requirements installed.
      {
        'nvim-telescope/telescope-fzf-native.nvim',
        -- NOTE: If you are having trouble with this installation,
        --       refer to the README for telescope-fzf-native for more instructions.
        build = 'make',
        cond = function()
          return vim.fn.executable 'make' == 1
        end,
      },
    },
  },


  'williamboman/mason.nvim',
  'williamboman/mason-lspconfig.nvim',
  'neovim/nvim-lspconfig',
  -- 'linrongbin16/gitlinker.nvim',

  -- Additional lua configuration, makes nvim stuff amazing!
  'folke/neodev.nvim',

  -- AUTO COMPLETE
  'hrsh7th/nvim-cmp',
  'hrsh7th/cmp-nvim-lsp',

  -- snippet
  "L3MON4D3/LuaSnip",
  'saadparwaiz1/cmp_luasnip',
  "rafamadriz/friendly-snippets",

  -- COQ
  -- 'ms-jpq/coq_nvim',
  -- 'ms-jpq/coq.artifacts',
  -- 'ms-jpq/coq.thirdparty',

  -- surround
  {
    "kylechui/nvim-surround",
    version = "*", -- Use for stability; omit to use `main` branch for the latest features
    event = "VeryLazy",
    config = function()
      require("nvim-surround").setup({
        -- Configuration here, or leave empty to use defaults
      })
    end
  },

  {
    'm4xshen/autoclose.nvim',
    config = function()
      require("autoclose").setup({
        -- Configuration here, or leave empty to use defaults
        keys = {
          ["("] = { escape = false, close = true, pair = "()" },
          ["["] = { escape = false, close = true, pair = "[]" },
          ["{"] = { escape = false, close = true, pair = "{}" },
          ["<"] = { escape = false, close = true, pair = "<>" },

          [">"] = { escape = true, close = false, pair = "<>" },
          [")"] = { escape = true, close = false, pair = "()" },
          ["]"] = { escape = true, close = false, pair = "[]" },
          ["}"] = { escape = true, close = false, pair = "{}" },

          ['"'] = { escape = true, close = true, pair = '""' },
          ["'"] = { escape = true, close = true, pair = "''" },
          ["`"] = { escape = true, close = true, pair = "``" },
        },
        options = {
          disabled_filetypes = { "text" },
          disable_when_touch = false,
          touch_regex = "[%w(%[{]",
          pair_spaces = false,
          auto_indent = true,
          disable_command_mode = false,
        },
      })
    end
  },

  -- {
  --   'windwp/nvim-autopairs',
  --   event = "InsertEnter",
  --   opts = {} -- this is equalent to setup({}) function
  -- },

  -- comments
  -- {
  --   'numToStr/Comment.nvim',
  -- },
  {
  'numToStr/Comment.nvim',
  config = function ()
    require('Comment').setup {
      pre_hook = function()
        return vim.bo.commentstring
      end
    }
  end,
  lazy = false,
  dependencies = {
    "JoosepAlviste/nvim-ts-context-commentstring",
    'nvim-treesitter/nvim-treesitter',
  }
  },

  -- 'ts_context_commentstring',
  -- 'JooepAlviste/nvim-ts-context-commentstring',


  -- Git related plugins
  'tpope/vim-fugitive',
  'tpope/vim-rhubarb',

  -- notes
  {
    'renerocksai/telekasten.nvim',
    dependencies = {
      'nvim-telescope/telescope.nvim',
      'nvim-lua/plenary.nvim'
    }
  },

  {
    -- Adds git related signs to the gutter, as well as utilities for managing changes
    'lewis6991/gitsigns.nvim',
    opts = {
      -- See `:help gitsigns.txt`
      signs = {
        add = { text = '+' },
        change = { text = '~' },
        delete = { text = '_' },
        topdelete = { text = '‾' },
        changedelete = { text = '~' },
      },
      on_attach = function(bufnr)
        vim.keymap.set('n', '<leader>ph', require('gitsigns').preview_hunk, { buffer = bufnr, desc = 'Preview git hunk' })

        -- -- don't override the built-in and fugitive keymaps
        -- local gs = package.loaded.gitsigns
        -- vim.keymap.set({ 'n', 'v' }, ']c', function()
        --   if vim.wo.diff then
        --     return ']c'
        --   end
        --   vim.schedule(function()
        --     gs.next_hunk()
        --   end)
        --   return '<Ignore>'
        -- end, { expr = true, buffer = bufnr, desc = 'Jump to next hunk' })
        -- vim.keymap.set({ 'n', 'v' }, '[c', function()
        --   if vim.wo.diff then
        --     return '[c'
        --   end
        --   vim.schedule(function()
        --     gs.prev_hunk()
        --   end)
        --   return '<Ignore>'
        -- end, { expr = true, buffer = bufnr, desc = 'Jump to previous hunk' })
      end,
    },
  },
}

local opts = {}

require('lazy').setup(plugins, opts)
