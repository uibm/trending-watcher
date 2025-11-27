import { setFailed, info } from "@actions/core";
import { getOctokit } from "@actions/github";
import fetch from "node-fetch";
import { JSDOM } from "jsdom";

const token = process.env.GITHUB_TOKEN;
const fullRepo = process.env.GITHUB_REPOSITORY;
const [owner, repo] = fullRepo.split("/");

const client = getOctokit(token);

async function getIssuesNeedingDeepWiki() {
  const { data } = await client.rest.issues.listForRepo({
    owner,
    repo,
    state: "open",
    labels: "trending",
    per_page: 100,
  });
  return data.filter(i =>
    i.labels.some(l => l.name === "initial review done") &&
    !i.labels.some(l => l.name === "deepwiki reviewed")
  );
}

async function scrapeDeepWiki(toOwner, toRepo, retries = 3) {
  const url = `https://deepwiki.com/${toOwner}/${toRepo}`;

  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const res = await fetch(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; TrendingWatcher/1.0; +https://github.com/trending-watcher)'
        }
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const html = await res.text();
      const dom = new JSDOM(html);
      const doc = dom.window.document;

      // Extract useful information from DeepWiki
      const data = {
        description: extractDescription(doc),
        technologies: extractTechnologies(doc),
        features: extractFeatures(doc),
        insights: extractInsights(doc),
      };

      return data;
    } catch (e) {
      if (attempt < retries - 1) {
        // Exponential backoff: 2s, 4s, 8s
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt + 1) * 1000));
      } else {
        throw e;
      }
    }
  }
}

function extractDescription(doc) {
  // Try to find main description
  const selectors = [
    '.description',
    '.repo-description',
    'meta[name="description"]',
    'p:first-of-type'
  ];

  for (const selector of selectors) {
    const elem = doc.querySelector(selector);
    if (elem) {
      const text = selector.includes('meta')
        ? elem.getAttribute('content')
        : elem.textContent.trim();
      if (text && text.length > 20) {
        return text.slice(0, 500);
      }
    }
  }

  return null;
}

function extractTechnologies(doc) {
  const technologies = new Set();

  // Look for technology badges, tags, or keywords
  const techElements = doc.querySelectorAll('.technology, .tech-tag, .badge, .topic-tag');
  techElements.forEach(elem => {
    const text = elem.textContent.trim();
    if (text && text.length < 30) {
      technologies.add(text);
    }
  });

  // Look for common tech keywords in text
  const content = doc.body.textContent.toLowerCase();
  const commonTech = ['python', 'javascript', 'typescript', 'rust', 'go', 'java', 'ruby',
                      'react', 'vue', 'angular', 'node.js', 'docker', 'kubernetes',
                      'tensorflow', 'pytorch', 'machine learning', 'ai', 'web3', 'blockchain'];

  commonTech.forEach(tech => {
    if (content.includes(tech.toLowerCase())) {
      technologies.add(tech);
    }
  });

  return Array.from(technologies).slice(0, 8);
}

function extractFeatures(doc) {
  const features = [];

  // Look for bullet points or feature lists
  const listItems = doc.querySelectorAll('li');
  listItems.forEach(li => {
    const text = li.textContent.trim();
    // Look for feature-like content (starts with action words or has reasonable length)
    if (text.length > 20 && text.length < 200 &&
        (text.match(/^(supports?|provides?|enables?|allows?|includes?|offers?|features?)/i) ||
         text.includes('✓') || text.includes('•'))) {
      features.push(text);
    }
  });

  return features.slice(0, 5);
}

function extractInsights(doc) {
  // Extract any highlighted insights or key points
  const insights = [];

  const highlightSelectors = [
    '.highlight',
    '.key-point',
    '.insight',
    'blockquote',
    'strong',
    'em'
  ];

  highlightSelectors.forEach(selector => {
    const elements = doc.querySelectorAll(selector);
    elements.forEach(elem => {
      const text = elem.textContent.trim();
      if (text.length > 30 && text.length < 300) {
        insights.push(text);
      }
    });
  });

  return insights.slice(0, 3);
}

function formatDeepWikiComment(targetRepo, data, url) {
  let comment = `### 🔍 Enhanced Review via DeepWiki\n\n`;
  comment += `**Repository:** ${targetRepo}\n`;
  comment += `**DeepWiki Link:** [View on DeepWiki](${url})\n\n`;

  if (data.description) {
    comment += `**📋 Description:**\n> ${data.description}\n\n`;
  }

  if (data.technologies && data.technologies.length > 0) {
    comment += `**🛠️ Technologies:**\n`;
    comment += data.technologies.map(t => `\`${t}\``).join(' • ');
    comment += `\n\n`;
  }

  if (data.features && data.features.length > 0) {
    comment += `**✨ Key Features:**\n`;
    data.features.forEach(f => {
      comment += `- ${f}\n`;
    });
    comment += `\n`;
  }

  if (data.insights && data.insights.length > 0) {
    comment += `**💡 Insights:**\n`;
    data.insights.forEach(i => {
      comment += `> ${i}\n\n`;
    });
  }

  comment += `\n---\n`;
  comment += `*This review is powered by [DeepWiki](https://deepwiki.com) - an AI-powered documentation platform.*\n`;
  comment += `*Part of the Trending Repo Journal project using GitHub Actions.*`;

  return comment;
}

async function run() {
  try {
    const issues = await getIssuesNeedingDeepWiki();
    info(`Found ${issues.length} issue(s) needing DeepWiki review.`);

    for (const issue of issues) {
      const targetRepo = issue.title.replace(/^Check trending repo:\s*/, "");
      const [toOwner, toRepo] = targetRepo.split("/");

      if (!toOwner || !toRepo) {
        info(`Skipping invalid repo format: ${targetRepo}`);
        continue;
      }

      try {
        const url = `https://deepwiki.com/${toOwner}/${toRepo}`;
        info(`Scraping DeepWiki for ${targetRepo}...`);

        const data = await scrapeDeepWiki(toOwner, toRepo);
        const commentBody = formatDeepWikiComment(targetRepo, data, url);

        await client.rest.issues.createComment({
          owner,
          repo,
          issue_number: issue.number,
          body: commentBody,
        });

        await client.rest.issues.addLabels({
          owner,
          repo,
          issue_number: issue.number,
          labels: ["deepwiki reviewed"],
        });

        info(`✓ Added DeepWiki review for ${targetRepo}`);

        // Rate limiting: wait 2 seconds between requests
        await new Promise(resolve => setTimeout(resolve, 2000));

      } catch (e) {
        info(`Failed to process ${targetRepo}: ${e.message}`);

        // Add a comment indicating failure
        await client.rest.issues.createComment({
          owner,
          repo,
          issue_number: issue.number,
          body: `### ⚠️ DeepWiki Review Unavailable\n\nCould not fetch enhanced information from DeepWiki for this repository.\n\n*Error: ${e.message}*`,
        });

        // Still mark as reviewed to avoid retry loops
        await client.rest.issues.addLabels({
          owner,
          repo,
          issue_number: issue.number,
          labels: ["deepwiki reviewed"],
        });
      }
    }

    info(`Processed ${issues.length} issue(s) with DeepWiki reviews.`);
  } catch (err) {
    setFailed(err.message);
  }
}

run();
