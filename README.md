# European Parliamentary AI Usage

I read The Economist's article "AI-written speeches are taking over politics" which uses [Pangram](pangram.com) to show the proliferation of AI-written speeches in selected anglophone countries. This repository aims to reproduce this research for six non-anglophone European parliaments: Germany, the Netherlands, Poland, France, Spain, and Italy.

The repository includes:
- Data collection scripts for the six mentioned countries
- The option to limit the study to a specific API-spend budget
- Saves all responses to enable arbitrary re-analysis of the data after collection (split by party/age/etc, perhaps)
- Random sampling per country/month if not all speeches can be used due to budget
- Automatic plot generation
- In case of an unbudgeted full run, grouping of speeches by speaker for analysis of individuals

Basically, it's ready for a Pangram API key. The project would take significant funds so I'm looking for a research grant.

For a more detailed (albeit AI-written) breakdown of features, read the [README for agents](AGENT_README.md).
