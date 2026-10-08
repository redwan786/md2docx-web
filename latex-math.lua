-- ```latex code blocks -> real display equations
function CodeBlock(el)
  if el.classes:includes('latex') or el.classes:includes('tex') or el.classes:includes('math') then
    return pandoc.Para({ pandoc.Math('DisplayMath', el.text) })
  end
end
