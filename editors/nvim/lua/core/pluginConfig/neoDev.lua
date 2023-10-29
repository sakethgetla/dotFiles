-- Automatically configures lua-language-server for your Neovim config, Neovim runtime and plugin directories
-- Annotations for completion, hover and signatures of:
-- Vim functions
-- Neovim api functions
-- vim.opt
-- vim.loop
-- properly configures the require path.
-- adds all plugins in opt and start to the workspace so you get completion for all installed plugins
-- properly configure the vim runtime

-- Setup neovim lua configuration
require('neodev').setup()
