# Projects & Case Studies

## Shopify gift-card credit exchange (multi-brand platform)
Built an "Exchange Subscription Credits" feature that converts paid subscription invoices into Shopify gift cards through the Shopify Admin GraphQL API. Used metafield-based idempotency so a single invoice can never be converted twice, and brand-scoped isolation so each storefront only sees its own customers' credits.

## Multi-store customer and address sync
Built sync methods that keep customers and addresses consistent across multiple Shopify stores and the CodeIgniter platform.

## Per-site configuration refactor
Refactored a centralised store lookup into a decentralised per-site config pattern, so new brands can be launched by configuration instead of code changes. Also built a multi-domain category navigation menu configurable per domain.

## Shopify automation and theme work
Shopify Flow automations (discount coupons, refund notifications), Checkout Extensibility, Liquid customer-account templates, CSV imports, multi-market pricing, and a theme-level script that localises contact details for US visitors. Migrated club-discount.com from WordPress to Shopify.

## PromptSuite - AI SaaS
Built a full AI SaaS platform with a FastAPI backend, Next.js frontend and Paddle billing. Supports text and image conversion modes.

## AI Digital Twin (this chatbot)
Agentic career assistant built with OpenAI tool calling and Gradio: RAG over my documents, a SQLite FAQ that learns from my answers, an evaluator LLM that checks every reply, and a Telegram console for human-in-the-loop answers.

## AI Shopify content generator (in progress)
Portfolio project: generates Shopify product content with LLMs.

## Sales analytics dashboard (planned)
Portfolio project: analytics dashboard for e-commerce sales data.
