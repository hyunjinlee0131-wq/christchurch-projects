# Launch notes: sewer pipe blockages and tree roots

## Post draft (story first, under 250 words)

> **Do street trees really block our sewers? I checked 32,000 Christchurch pipes.**
>
> Every time a sewer blocks, someone blames tree roots. The council publishes open data on every sewer pipe (its
> material, size, age and how many blockages it has had) and on about 183,000 street and park trees. So I put them
> together.
>
> What I found:
> - **Size and age matter most.** Small, old pipes block far more: about +15% for every extra 10 years, and roughly
>   two-thirds fewer blockages for every extra 100 mm of width.
> - **Old asbestos-cement and concrete pipes** block about 1.5–1.7× as often as plastic, all else equal.
> - **Street trees?** After allowing for all of that, there's **no clear sign** that a council tree near a pipe makes
>   it block more. That doesn't clear roots; it points at *private* garden trees, which aren't in open data.
> - A model that ranks every pipe puts **31% of recorded blockages in the riskiest 10% of the network**, nearly
>   double what you'd get by targeting old materials alone.
>
> You can search your own street and see the riskiest pipes on a map:
> 👉 https://hyunjinlee0131-wq.github.io/christchurch-projects/pipes/
>
> If you work in three waters, I'd love to know what the data is missing. CCTV defect codes and blockage dates
> would make this much sharper.

## Where to post
- **LinkedIn:** asset management, three waters and Water New Zealand networks. Lead with "31% of blockages in 10%
  of pipe" and the tree finding.
- **r/chch:** the tree myth-check angle, with the street search link.
- **Local arborist and tree advocacy groups:** the "street trees aren't the problem in this data" finding,
  with its caveats.

## First-week checks
- 👍/👎 on the site and in the app (Supabase `feedback`, `project = pipe_blockages`).
- Streamlit Cloud viewer analytics: how many people open the tool, and whether they use street search.
- Any message from council staff. Ask whether dated blockage records or CCTV codes can be shared.
