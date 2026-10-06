if ! get(b:, "removed_vimwiki_bufwritepre", 0)
  augroup vimwiki
    au! BufWritePre <buffer>
  augroup END
  let b:removed_vimwiki_bufwritepre = 1
endif
