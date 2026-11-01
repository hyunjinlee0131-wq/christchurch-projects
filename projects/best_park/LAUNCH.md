# Launch notes: Best Park in Christchurch

## Post draft (story first, under 250 words)

> **I ranked all 994 parks in Christchurch. Jellie Park came top. Do you agree?**
>
> Every weekend we have the same argument: which park are we taking the kids to? Ours has a playground, but is it a
> *good* one? Is there anywhere to sit, a tap, a barbecue, room for the dog?
>
> It turns out the council publishes open data on almost everything in its parks: every seat, picnic table,
> barbecue, drinking fountain, piece of play equipment, sports field and tree. So I counted it all, park by park,
> and turned it into a ranking.
>
> By the data, the top three are **Jellie Park, Halswell Domain and Burnside Park**. Hagley Park is only around #55,
> mostly because it has fewer playgrounds and seats per park than the suburban sports parks.
>
> But data can't measure a view or a great coffee cart, so you can do two things:
> - **move the sliders** ("I have a dog", "I don't care about sport") and get your own ranking, or parks near you;
> - **vote for the parks you love.** There's a People's Choice list, and a "Data vs People" list of the parks the
>   numbers underrate.
>
> 👉 https://hyunjinlee0131-wq.github.io/christchurch-projects/parks/
>
> Tell me which park the data got wrong. That's the most useful thing you could post here.

## Where to post

- **r/chch**: the post above. Lead with the ranking question; people love arguing about parks.
- **Local Facebook groups**: Christchurch parents' groups and dog-owner groups. Use the "I have a dog" angle with a
  screenshot of the dog-weighted ranking.
- **LinkedIn**: a shorter version about open data ("994 parks, 10 council datasets, one evening"), linking to the
  GitHub repo.
- **Community boards / residents' associations**: the per-park pages ("Your local park is #212. Here's why").

## First-week checks

- Votes and 👍/👎 counts in the Supabase Table Editor (needs `SETUP.md` § Supabase done first).
- GA4 events: `open_park`, `reweight`, `near_me`, `share`, `vote`, `feedback`. A high `reweight` count means the
  sliders are the hook; low `vote` with high traffic means the vote button needs to be more prominent.
- Read every "Tell us more" response. Wrong-data reports go back into the pipeline as cleaning rules.
