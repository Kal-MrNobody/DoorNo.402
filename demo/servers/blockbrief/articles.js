module.exports = Array.from({ length: 10 }, (_, i) => ({
  slug: `daily-briefing-${i + 1}`,
  title: `On-Chain Briefing Vol. ${i + 1}`,
  preview: `A deep dive into the on-chain metrics for week ${i + 1}...`,
  content: `Full article content for briefing ${i + 1}...`
}));
