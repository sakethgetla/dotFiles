--
-- require("image").setup({
--   backend = "kitty",
--   processor = "magick_cli", -- or "magick_rock"
--   integrations = {
--     markdown = {
--       enabled = true,
--       clear_in_insert_mode = false,
--       download_remote_images = true,
--       only_render_image_at_cursor = false,
--       only_render_image_at_cursor_mode = "popup",
--       floating_windows = false, -- if true, images will be rendered in floating markdown windows
--       filetypes = { "markdown", "vimwiki" }, -- markdown extensions (ie. quarto) can go here
--     },
--     neorg = {
--       enabled = true,
--       filetypes = { "norg" },
--     },
--     typst = {
--       enabled = true,
--       filetypes = { "typst" },
--     },
--     html = {
--       enabled = false,
--     },
--     css = {
--       enabled = false,
--     },
--   },
--   max_width = nil,
--   max_height = nil,
--   max_width_window_percentage = nil,
--   max_height_window_percentage = 50,
--   window_overlap_clear_enabled = false, -- toggles images when windows are overlapped
--   window_overlap_clear_ft_ignore = { "cmp_menu", "cmp_docs", "snacks_notif", "scrollview", "scrollview_sign" },
--   editor_only_render_when_focused = false, -- auto show/hide images when the editor gains/looses focus
--   tmux_show_only_in_active_window = false, -- auto show/hide images in the correct Tmux window (needs visual-activity off)
--   hijack_file_patterns = { "*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.avif" }, -- render image files as images when opened
-- })

---@class snacks.image.Config
---@field enabled? boolean enable image viewer
---@field wo? vim.wo|{} options for windows showing the image
---@field bo? vim.bo|{} options for the image buffer
---@field formats? string[]
--- Resolves a reference to an image with src in a file (currently markdown only).
--- Return the absolute path or url to the image.
--- When `nil`, the path is resolved relative to the file.
---@field resolve? fun(file: string, src: string): string?
---@field convert? snacks.image.convert.Config

-- require("snacks").setup(
--   {
--     formats = {
--       "png",
--       "jpg",
--       "jpeg",
--       "gif",
--       "bmp",
--       "webp",
--       "tiff",
--       "heic",
--       "avif",
--       "mp4",
--       "mov",
--       "avi",
--       "mkv",
--       "webm",
--       "pdf",
--     },
--     force = false, -- try displaying the image, even if the terminal does not support it
--     doc = {
--       -- enable image viewer for documents
--       -- a treesitter parser must be available for the enabled languages.
--       enabled = true,
--       -- render the image inline in the buffer
--       -- if your env doesn't support unicode placeholders, this will be disabled
--       -- takes precedence over `opts.float` on supported terminals
--       inline = true,
--       -- render the image in a floating window
--       -- only used if `opts.inline` is disabled
--       float = true,
--       max_width = 80,
--       max_height = 40,
--       -- Set to `true`, to conceal the image text when rendering inline.
--       -- (experimental)
--       ---@param lang string tree-sitter language
--       ---@param type snacks.image.Type image type
--       conceal = function(lang, type)
--         -- only conceal math expressions
--         return type == "math"
--       end,
--     },
--     img_dirs = { "img", "images", "assets", "static", "public", "media", "attachments" },
--     -- window options applied to windows displaying image buffers
--     -- an image buffer is a buffer with `filetype=image`
--     wo = {
--       wrap = false,
--       number = false,
--       relativenumber = false,
--       cursorcolumn = false,
--       signcolumn = "no",
--       foldcolumn = "0",
--       list = false,
--       spell = false,
--       statuscolumn = "",
--     },
--     cache = vim.fn.stdpath("cache") .. "/snacks/image",
--     debug = {
--       request = false,
--       convert = false,
--       placement = false,
--     },
--     env = {},
--     -- icons used to show where an inline image is located that is
--     -- rendered below the text.
--     icons = {
--       math = "󰪚 ",
--       chart = "󰄧 ",
--       image = " ",
--     },
--     ---@class snacks.image.convert.Config
--     convert = {
--       notify = true, -- show a notification on error
--       ---@type snacks.image.args
--       mermaid = function()
--         local theme = vim.o.background == "light" and "neutral" or "dark"
--         return { "-i", "{src}", "-o", "{file}", "-b", "transparent", "-t", theme, "-s", "{scale}" }
--       end,
--       ---@type table<string,snacks.image.args>
--       magick = {
--         default = { "{src}[0]", "-scale", "1920x1080>" }, -- default for raster images
--         vector = { "-density", 192, "{src}[0]" }, -- used by vector images like svg
--         math = { "-density", 192, "{src}[0]", "-trim" },
--         pdf = { "-density", 192, "{src}[0]", "-background", "white", "-alpha", "remove", "-trim" },
--       },
--     },
--     math = {
--       enabled = true, -- enable math expression rendering
--       -- in the templates below, `${header}` comes from any section in your document,
--       -- between a start/end header comment. Comment syntax is language-specific.
--       -- * start comment: `// snacks: header start`
--       -- * end comment:   `// snacks: header end`
--       typst = {
--         tpl = [[
--           #set page(width: auto, height: auto, margin: (x: 2pt, y: 2pt))
--           #show math.equation.where(block: false): set text(top-edge: "bounds", bottom-edge: "bounds")
--           #set text(size: 12pt, fill: rgb("${color}"))
--           ${header}
--           ${content}]],
--       },
--       latex = {
--         font_size = "Large", -- see https://www.sascha-frank.com/latex-font-size.html
--         -- for latex documents, the doc packages are included automatically,
--         -- but you can add more packages here. Useful for markdown documents.
--         packages = { "amsmath", "amssymb", "amsfonts", "amscd", "mathtools" },
--         tpl = [[
--           \documentclass[preview,border=0pt,varwidth,12pt]{standalone}
--           \usepackage{${packages}}
--           \begin{document}
--           ${header}
--           { \${font_size} \selectfont
--             \color[HTML]{${color}}
--           ${content}}
--           \end{document}]],
--       },
--   },
-- })
