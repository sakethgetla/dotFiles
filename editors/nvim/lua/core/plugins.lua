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
  'nvim-treesitter/nvim-treesitter',
  {
    'nvim-telescope/telescope.nvim',
    branch = '0.1.x',
    dependencies = { 'nvim-lua/plenary.nvim' }
  },
  'williamboman/mason.nvim',
  'williamboman/mason-lspconfig.nvim',
  'neovim/nvim-lspconfig',
  -- 'linrongbin16/gitlinker.nvim',

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
}

local opts = {}

require('lazy').setup(plugins, opts)
