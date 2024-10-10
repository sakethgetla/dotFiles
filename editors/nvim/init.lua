require("core.set")

if vim.g.vscode then
  -- used for "vscode Neovim" plugin in vscode
  local vscode = require('vscode')


  -- vim.keymap.set("n", "<leader>h", "<C-w><C-h>")
  -- vim.keymap.set("n", "<leader>l", "<C-w><C-l>")
  -- vim.keymap.set("n", "<leader>j", "<C-w><C-j>")
  -- vim.keymap.set("n", "<leader>k", "<C-w><C-k>")

  -- general
  vim.keymap.set({ "n", }, "<leader>tr", function()
    vscode.action("workbench.action.terminal.toggleTerminal")
  end)

  vim.keymap.set({ "n", }, "<leader><enter>", function()
    vscode.action("workbench.action.toggleZenMode")
  end)

  vim.keymap.set({ "n", }, "<leader>ww", function()
    vscode.action("workbench.action.files.save")
  end)

  -- navigation
  vim.keymap.set({ "n", }, "<leader>h", function()
    vscode.action("workbench.action.navigateLeft")
  end)

  vim.keymap.set({ "n", }, "<leader>l", function()
    vscode.action("workbench.action.navigateRight")
  end)

  vim.keymap.set({ "n", }, "<leader>k", function()
    vscode.action("workbench.action.navigateAbove")
  end)

  vim.keymap.set({ "n", }, "<leader>j", function()
    vscode.action("workbench.action.navigateDown")
  end)

  vim.keymap.set({ "n", "x", "i" }, "<leader>tt", function()
    vscode.action("workbench.action.toggleSidebarVisibility")
  end)

  vim.keymap.set({ "n", "x", "i" }, "<leader>tr", function()
    -- vscode.action("workbench.action.toggleSidebarVisibility && workbench.explorer.fileView.focus")
    vscode.action("workbench.action.terminal.toggleTerminal")
    -- vscode.action("workbench.explorer.fileView.focus")
  end)

  -- VSCode extension
else
  -- ordinary Neovim
  require("core.keymap")
  require("core.plugin")
  require("core.pluginConfig")
end
