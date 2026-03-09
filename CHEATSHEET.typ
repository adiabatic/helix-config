#let darkMode = false

// Light-mode defaults
#let rawBackgroundColor = luma(90%)
#let textColor = black
#let pageBackground = none

#if darkMode == true {
  rawBackgroundColor = luma(30%)
  textColor = white
  pageBackground = box(fill: black, width: 13in, height: 13in)
}

#set page(
  paper: "us-letter",
  flipped: true,
  margin: .5in,
  // margin: 1cm,
  background: pageBackground,
  // Prints out
  footer: [
    Helix Cheatsheet
    #h(1fr)
    #datetime.today().display("[month repr:long] [day padding:none], [year]")
  ],
)

#set text(
  font: "Concourse OT 3",
  size: 13.5pt,
  fill: textColor,
)

#show raw: it => {
  set text(font: "Triplicate OT A")
  show: highlight.with(fill: rawBackgroundColor)
  it + sym.zws // workaround for bug: https://github.com/typst/typst/discussions/3111
}


#show: columns.with(3)
#show table.cell.where(colspan: 2): strong

#let mid-header(body) = {
  table.cell(
    colspan: 2,
    align: center,
    inset: (top: 16pt),
    [#body],
  )
}

#table(
  columns: 2,
  align: (right, left),
  // table.header[*Action*][*What*],
  stroke: none,
  mid-header[Popups],
  [`␣`], [open space menu],
  [`Ctrl-w`], [manage windows],
  [`z`/`Z`], [View-mode popup / and the cursor doesn’t move],
  [`g`], [Goto-mode popup],
  [`+`], [mostly-inserters popup],
  [`m`], [match popup ((remove) surround, etc.)],
  [`[`/`]`], [jump to things/add newlines],

  mid-header[Search-and-replace],
  [`/`/`?`], [find / backwards],
  [`n`/`N`], [find next/previous],
  [`*`], [`"/y` (copy selection to register `/`, used for find)],
  [`*vnnn`], [\[select something\] ⌘D⌘D⌘D],

  mid-header[Repetition],
  [`.`], [repeat last insert command],
  [`b".p`], [duplicate line downwards],

  mid-header[Jumping around],
  [`Ctrl-8`], [save current location in jumplist],
  [`Ctrl-i`], [move backward in jumplist],
  [`Ctrl-k`], [move forward in jumplist],
  [`␣j`],     [open jumplist picker],

  mid-header[Editing],
  [`t`/`T`], [insert mode],
  [`o`/`O`], [insert line below/above cursor],
  [`M`], [short for `ft`],
  [`vglf`], [delete until the end of the line],
  [`R`], [kill until end of line and insert],
  [`C-g`], [Join lines (^J in VS Code)],

  mid-header[Selecting],
  [`w`/`W`], [select subword   backwards / including `_`, etc.],
  [`e`/`E`], [select subword   forwards /  including `_`, etc.],
  [`s`/`S`], [select word      backwards / including `␣`, etc.],
  [`d`/`D`], [select word      forwards /  including `␣`, etc.],
  [`x`/`X`], [select long word backwards / including `␣`, etc.],
  [`c`/`C`], [select long word forwards /  including `␣`, etc.],
  [`%`], [⌘A],
  [`v`], [enter select mode (movement _extends_ selection)],
  [`b`], [select line (below)],
  [``` ` ```], [make multiple selections in selection with regex],
  [`~`], [split selection on regex],
  [`Alt-;`], [reverse selection (flip head and tail)],

  mid-header[Multiple cursors],
  [`C-u`], [⌥⌘↑],
  [`C-o`], [⌥⌘↓],
  [`;`], [collapse selection to single cursor],
  [`,`], [remove other cursors],
  [`Alt-,`], [deselect primary selection],
  [`Alt-s`], [split many-lined selection so each line has its own cursor (⌥⇧I)],
  [`Alt--`], [merge selections],
  [`(`/`)`], [cycle primary selection backward/forward through selections],
  [`Alt-)`/\ `Alt-(`], [cycle selections forward/backward (tip: use `|` in your searches)],

  mid-header[Piping],
  [`|`], [Pipe each selection through shell command, replacing with output],

  mid-header[Typeable commands],
  [`:lang`], [Set language (`markdown`, etc.)],
  // [`:config-reload`], [Reload config], // too wide, breaks layout
)
