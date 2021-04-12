;; Set up package.el to work with MELPA
(require 'package)


(add-to-list 'package-archives
             '("melpa" . "https://melpa.org/packages/"))
(package-initialize)
;;(package-refresh-contents)


;; Download Evil
;;(unless (package-installed-p 'evil)
;;  (package-install 'evil))
;; Enable Evil
(require 'evil)

(require 'evil-search-highlight-persist)
(require 'linum-relative)
(require 'lsp-mode)
(require 'evil-org)
(require 'evil-org-agenda)
(require 'evil-surround)
;;
;;
;;(setq load-prefer-newer t)
;;;;(add-to-list 'load-path "/path/to/packed")
;;(add-to-list 'load-path ".emacs.d/init.el")
;;(require 'auto-compile)
;;(auto-compile-on-load-mode)
;;(auto-compile-on-save-mode)


(evil-mode 1)
(evil-set-leader 'normal (kbd "SPC"))

(setq inhibit-startup-message t) ;; hide the startup message
;;(global-linum-mode t) ;; enable line numbers globally
;;(display-line-numbers-mode)
;;(setq display-line-numbers 'relative)
;;(when (version<= "26.0.50" emacs-version )
;;  (global-display-line-numbers-mode))
;; Disabling things
;;-----------------------------------------------------------------------

(linum-on)
;;(linum-relative-mode t)
(linum-relative-on)
(setq linum-relative-backend 'display-line-numbers-mode)
;;(setq-default display-line-numbers-mode t)
(global-linum-mode 1)


;;(shell)
(menu-bar-mode -1) 
(toggle-scroll-bar -1) 
(tool-bar-mode -1) 

(global-evil-search-highlight-persist t)
;;(set-face-background 'evil-ex-lazy-highlight "black")


;; You can use the following configuration to have all modes start in normal state:
(setq evil-emacs-state-modes nil)
(setq evil-insert-state-modes nil)
(setq evil-motion-state-modes nil)

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


(global-evil-surround-mode 1)
;;-----------------------------------------------------------------------
;;(global-evil-tabs-mode t)
;;
;;(define-key evil-normal-state-map (kbd "C-0") (lambda() (interactive) (elscreen-goto 0)))
;;;;(define-key evil-normal-state-map (kbd "C- ") (lambda() (interactive) (elscreen-goto 0)))
;;(define-key evil-normal-state-map (kbd "C-1") (lambda() (interactive) (elscreen-goto 1)))
;;(define-key evil-normal-state-map (kbd "C-2") (lambda() (interactive) (elscreen-goto 2)))
;;(define-key evil-normal-state-map (kbd "C-3") (lambda() (interactive) (elscreen-goto 3)))
;;(define-key evil-normal-state-map (kbd "C-4") (lambda() (interactive) (elscreen-goto 4)))
;;(define-key evil-normal-state-map (kbd "C-5") (lambda() (interactive) (elscreen-goto 5)))
;;(define-key evil-normal-state-map (kbd "C-6") (lambda() (interactive) (elscreen-goto 6)))
;;(define-key evil-normal-state-map (kbd "C-7") (lambda() (interactive) (elscreen-goto 7)))
;;(define-key evil-normal-state-map (kbd "C-8") (lambda() (interactive) (elscreen-goto 8)))
;;(define-key evil-normal-state-map (kbd "C-9") (lambda() (interactive) (elscreen-goto 9)))
;;(define-key evil-insert-state-map (kbd "C-0") (lambda() (interactive) (elscreen-goto 0)))
;;;;(define-key evil-insert-state-map (kbd "C- ") (lambda() (interactive) (elscreen-goto 0)))
;;(define-key evil-insert-state-map (kbd "C-1") (lambda() (interactive) (elscreen-goto 1)))
;;(define-key evil-insert-state-map (kbd "C-2") (lambda() (interactive) (elscreen-goto 2)))
;;(define-key evil-insert-state-map (kbd "C-3") (lambda() (interactive) (elscreen-goto 3)))
;;(define-key evil-insert-state-map (kbd "C-4") (lambda() (interactive) (elscreen-goto 4)))
;;(define-key evil-insert-state-map (kbd "C-5") (lambda() (interactive) (elscreen-goto 5)))
;;(define-key evil-insert-state-map (kbd "C-6") (lambda() (interactive) (elscreen-goto 6)))
;;(define-key evil-insert-state-map (kbd "C-7") (lambda() (interactive) (elscreen-goto 7)))
;;(define-key evil-insert-state-map (kbd "C-8") (lambda() (interactive) (elscreen-goto 8)))
;;(define-key evil-insert-state-map (kbd "C-9") (lambda() (interactive) (elscreen-goto 9)))

;;-----------------------------------------------------------------------

(evil-define-key 'normal 'global (kbd "<leader>fs") 'save-buffer)
(evil-define-key 'normal 'global (kbd "<leader>.") 'find-file)
(evil-define-key 'normal 'global (kbd "<leader>bi") 'buffer-menu)
(evil-define-key 'normal 'global (kbd "<leader>fr") 'recentf-open-files)
(evil-define-key 'normal 'global (kbd "<leader>t") 'treemacs)
(evil-define-key 'normal 'global (kbd "<leader>v") 'split-window-vertically)
(evil-define-key 'normal 'global (kbd "<leader>h") 'evil-window-left)
(evil-define-key 'normal 'global (kbd "<leader>j") 'evil-window-down)
(evil-define-key 'normal 'global (kbd "<leader>k") 'evil-window-up)
(evil-define-key 'normal 'global (kbd "<leader>l") 'evil-window-right)
(evil-define-key 'normal 'global (kbd "<leader>q") 'evil-quit)
(evil-define-key 'normal 'global (kbd "<leader><return>") 'bookmark-bmenu-list)
;;(evil-define-key 'normal 'global (kbd "<leader>r") 'evil-quit)

(add-hook 'python-mode-hook 'lsp)
;;(add-hook 'python-mode-hook #'lsp)

(add-hook 'org-mode-hook 'evil-org-mode)
(evil-org-set-key-theme '(navigation insert textobjects additional calendar))

(evil-org-agenda-set-keys)


(load-theme 'gruvbox-dark-hard t)
(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(package-selected-packages
   '(evil-search-highlight-persist evil-surround evil-org auto-compile magit linum-relative lsp-pyright lsp-python-ms company flycheck helm-lsp lsp-ivy lsp-treemacs lsp-ui org-journal evil-nerd-commenter treemacs-evil gruvbox-theme undo-fu undo-tree evil)))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )
