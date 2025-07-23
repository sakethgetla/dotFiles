-- leader keys need to be set first
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

require("core.lazy")
require("core.keymap")
require("core.settings")

-- plugins already impored in config.lazy
-- import all files in pluginsConfig
require("pluginsConfig.tree")
require("pluginsConfig.treeSitter")
require("pluginsConfig.fuzzyFind")
require("pluginsConfig.notes")
require("pluginsConfig.image")
