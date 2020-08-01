const md = require("markdown-it")({
  html: true, // Enable HTML tags in source
  breaks: true, // Convert '\n' in paragraphs into <br>
  linkify: true, // Autoconvert URL-like text to links
});
const emoji = require('markdown-it-emoji');
const fs = require("fs");
const Parser = require("rss-parser");

const parser = new Parser();

const feedUrl = "https://medium.com/feed/@harikrishnan";
const blogPostLimit = 6;

md.use(emoji);

(async () => {
  let blogPosts = "";
  try {
    blogPosts = await loadBlogPosts();
  } catch (e) {
    console.error(`Failed to load blog posts from ${websiteUrl}`, e);
  }

  static = fs.readFileSync("./static.md")
  text = `${static}${blogPosts}`;

  const result = md.render(text);

  fs.writeFile("README.md", result, function (err) {
    if (err) return console.log(err);
    console.log(`${result} > README.md`);
  });
})();

async function loadBlogPosts() {
  const feed = await parser.parseURL(feedUrl);

  let links = "";

  feed.items.filter(item => !item.title.includes("Thank")).slice(0, blogPostLimit).forEach((item) => {
    links += `<li><a href=${item.link}>${item.title}</a></li>`;
  });

  return `
  <ul>
    ${links}
  </ul>\n
  [:arrow_right: More blog posts](https://medium.com/polarizertech)
  `;
}