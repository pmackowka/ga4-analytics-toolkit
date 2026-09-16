# GTM implementation snippets

Custom JavaScript variables/tagi z realnych wdrożeń GTM.

- **`session-storage-promotion-name.js`** — zapamiętuje w `sessionStorage` nazwę i ID aktualnie oglądanej promocji (`view_promotion`/`select_promotion`), żeby można było powiązać z nią kolejne zdarzenie e-commerce (np. `add_to_cart`) mimo że GA4 nie przekazuje tego kontekstu automatycznie między eventami.
