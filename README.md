# `~/.config/helix/`

I like Helix but I wanted to see if I could make the thing a teeny bit more like [WordStar](https://sfwriter.com/wordstar.htm), particularly when it comes to movement.

The main adjustments are:

- ikjl for ↑↓←→ instead of hjkl for ←↓↑→
- forward/back by words (broadly defined) are we/sd/xc and their uppercase counterparts
- jumping around by fractions of a screenful are done by holding Ctrl and pressing er/df/cv

…and other commands need to be either moved (like d → f) or removed entirely (like ft/FT).

I was pleasantly surprised to discover that rearranging moderate amounts of functionality didn’t turn into an awful weekend-long juggling act.

## Known bugs and limitations

Not all instances of d-to-delete are replaced with f, and that sort of thing.
