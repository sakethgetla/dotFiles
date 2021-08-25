;; Set up package.el to work with MELPA
(require 'package)
(add-to-list 'package-archives
             '("melpa" . "https://melpa.org/packages/"))
(package-initialize)
;;(package-refresh-contents)

;; Download Evil
(unless (package-installed-p 'evil)
  (package-install 'evil))

;; Enable Evil
(require 'evil)
;; Download Evil
(unless (package-installed-p 'evil)
  (package-install 'evil)
  (package-install 'company)
  (package-install 'lsp-mode)
  (package-install 'evil-org)
  (package-install 'evil-surround)
  (package-install 'org-journal)
  (package-install 'undo-tree)
  (package-install 'flycheck)
  (package-install 'rjsx-mode)
)

 ;;Enable Evil
(require 'evil)

;;(require 'evil-search-highlight-persist)
(require 'linum-relative)
;;(require 'jedi)
(require 'lsp-mode)
(require 'evil-org)
;;(require 'evil-org-agenda)
(require 'evil-surround)
(require 'org-journal)
(require 'undo-tree)
(require 'flycheck)
(require 'rjsx-mode)
;;(require 'rjsxialkwef-mode)


(require 'evil-surround)
(global-evil-surround-mode 1)



(evil-mode 1)
(evil-set-leader 'normal (kbd "SPC"))


(global-undo-tree-mode)

(setq inhibit-startup-message t) ;; hide the startup message
(setq visible-bell 1)
(tool-bar-mode -1)
(menu-bar-mode -1)
(scroll-bar-mode -1)

(require 'lsp-mode)
(add-hook 'js-mode-hook #'lsp)


(linum-on)
;;(linum-relative-mode t)
(linum-relative-on)
(setq linum-relative-backend 'display-line-numbers-mode)
;;(setq-default display-line-numbers-mode t)
(global-linum-mode 1)


;;(global-evil-surround-mode 1)

;; no backup files
(setq create-lockfiles nil)

;;(setq make-backup-files nil)
(setq backup-directory-alist `(("." . "~/.saves")))

(setq org-journal-dir "~/docs/.p/journals/")

;; You can use the following configuration to have all modes start in normal state:
(setq evil-emacs-state-modes nil)
(setq evil-insert-state-modes nil)
(setq evil-motion-state-modes nil)

(setq-default indent-tabs-mode nil)

;;Note: If, after turning any of these off, you want to re-enable them for a single emacs window, you can do so by pressing Meta-x and then typing the command at the M-x prompt. (Copied from Web)
;;Example:
;;M-x tool-bar-mode
;;will turn the toolbar back on. 
;;-----------------------------------------------------------------------
(setq evil-emacs-state-cursor '("blue" box))
(setq evil-normal-state-cursor '("green" box))
(setq evil-visual-state-cursor '("orange" box))
(setq evil-insert-state-cursor '("red" bar))
(setq evil-replace-state-cursor '("red" bar))
(setq evil-operator-state-cursor '("red" hollow))


(evil-define-key 'normal 'global (kbd "<leader>fs") 'save-buffer)
(evil-define-key 'normal 'global (kbd "<leader>.") 'find-file)
(evil-define-key 'normal 'global (kbd "<leader>bi") 'buffer-menu)
(evil-define-key 'normal 'global (kbd "<leader>gg") 'magit)
(evil-define-key 'normal 'global (kbd "<leader>fr") 'recentf-open-files)
(evil-define-key 'normal 'global (kbd "<leader>t") 'treemacs)
;;(evil-define-key 'normal 'global (kbd "<leader>t") 'neotree-toggle)
;;(evil-define-key 'normal neotree-mode (kbd "<return>") 'neotree-enter)
(evil-global-set-key 'normal (kbd "<return>") 'treemacs-RET-action)
(evil-define-key 'normal 'global (kbd "<leader>v") 'split-window-vertically)
(evil-define-key 'normal 'global (kbd "<leader>V") 'split-window-horizontally)
(evil-define-key 'normal 'global (kbd "<leader>q") 'evil-quit)
(evil-define-key 'normal 'global (kbd "<leader><return>") 'bookmark-bmenu-list)
(evil-define-key 'normal 'global (kbd "u") 'undo-tree-undo)
(evil-define-key 'normal 'global (kbd "C-r") 'undo-tree-redo)
;;(evil-define-key 'normal 'global (kbd "<leader>r") 'evil-quit)

;; move focus
(evil-define-key 'normal 'global (kbd "<leader>h") 'evil-window-left)
(evil-define-key 'normal 'global (kbd "<leader>j") 'evil-window-down)
(evil-define-key 'normal 'global (kbd "<leader>k") 'evil-window-up)
(evil-define-key 'normal 'global (kbd "<leader>l") 'evil-window-right)


;; move window
(evil-define-key 'normal 'global (kbd "<leader>H") 'evil-window-move-far-left)
(evil-define-key 'normal 'global (kbd "<leader>J") 'evil-window-move-very-bottom)
(evil-define-key 'normal 'global (kbd "<leader>K") 'evil-window-move-very-top)
(evil-define-key 'normal 'global (kbd "<leader>L") 'evil-window-move-far-right)

 
(add-hook 'org-mode-hook 'evil-org-mode)
(add-hook 'python-mode-hook 'jedi:setup)
(add-to-list 'auto-mode-alist '("\\/.*\\.tsx\\'" . rjsx-mode))
 
(load-theme 'gruvbox-dark-hard t)
 
;;(global-evil-surround-mode 1)
(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(package-selected-packages
   '(lsp-treemacs flycheck undo-tree org-journal magit lsp-mode linum-relative gruvbox-theme evil company)))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )
