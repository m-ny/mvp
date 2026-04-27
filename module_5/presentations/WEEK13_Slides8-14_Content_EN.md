# Week 13 Final Deck - Slides 8-13 Content

Concise slide copy aligned with the latest speaker script.  
All claims below are grounded in repo artifacts, mainly:

- `module_5/run_log.json`
- `module_5/EVAL_REPORT.md`
- `module_5/eval_agent.py`
- `module_5/system-prompt v2.md`

---

## Slide 8 - The Reality vs. The Impact

### Headline

**From manual guesswork to qualified outreach**

### On-slide content

**Reality**

- Manual outreach fatigue
- Low message volume
- Inconsistent follow-up quality

**Impact**

- More relevant reasons to reach out
- Better message quality at scale
- Higher chance of meaningful boutique conversations

### Layout note

Use a simple **left/right contrast**:

- left = Reality
- right = Impact

---

## Slide 9 - The Inputs

### Headline

**Three inputs make outreach grounded**

### On-slide content

**Client memory**

- preferences
- past conversations
- life events

**Trend signals**

- what matters now
- why it is relevant

**Product catalog**

- real products
- real attributes
- real directions

**Footer line**
Grounded in memory, market signal, and product reality.

### Source alignment

- Product truth and input/output structure: `module_5/system-prompt v2.md`

---

## Slide 10 - The Outputs

### Headline

**Two adapted outputs show how the agent personalizes outreach**

### On-slide content

### Final slide-ready version

**Left card - Lin Wanqing**

- **Profile**: VIC; Hong Kong Art Week; understated, no-logo taste
- **Product direction**: Elsa Peretti Color by the Yard Pendant; Elsa Peretti Open Heart Pendant
- **Message (CN)**:  
“林小姐，前阵子想到您提过下个月要去香港艺术周，也记得您一直偏好低调但有质感的东西。我这两天留了两件线条很干净的 Tiffany 项链，和风衣搭在一起会很轻松。如果您愿意，我晚点整理两张参考图发您。”
- **Message (EN)**:  
“Lin, I was thinking about your Hong Kong Art Week trip next month and remembered how much you prefer pieces that feel refined and understated. I set aside two Tiffany necklaces with very clean lines that would pair easily with a coat. If helpful, I can send you a couple of reference images later.”

**Right card - He Yawen**

- **Profile**: Gold; coming-of-age gift for daughter; classic and long-lasting taste
- **Product direction**: Return to Tiffany Love Lock Necklace; Elsa Peretti Open Heart Pendant; Tiffany Knot Pendant
- **Message (CN)**:  
“何女士，前阵子您提过想给女儿挑一件能戴很多年的成人礼礼物，我这两天又想到几款线条很干净、以后也不容易过时的 Tiffany 项链和吊坠，比较适合这种纪念场合。如果您愿意，我可以先整理两三个经典款发您参考。”
- **Message (EN)**:  
“Ms. He, I remembered you were looking for a coming-of-age gift your daughter could keep for many years. A few Tiffany necklaces and pendants came to mind that feel clean, classic, and right for a milestone like this. If you’d like, I can first send over two or three timeless options for reference.”

**Bottom caption**
Both outputs follow the same logic: memory -> product direction -> low-pressure outreach.

### Visual recommendation

- Two equal-width case cards
- One short product row under each name
- Chinese message first, English translation below in smaller text
- Caption centered at the bottom

### Source alignment

- Output structure: `module_5/system-prompt v2.md`
- Base cases: `module_5/run_log.json`, `module_5/benchmark/benchmark_clients.json`
- Tiffany product references:
  - [Elsa Peretti Color by the Yard Pendant](https://www.tiffany.com/jewelry/necklaces-pendants/ep-color-by-the-yard-platinum-sapphire-necklaces-pendants-1425540342.html)
  - [Elsa Peretti Open Heart Pendant](https://www.tiffany.com/jewelry/necklaces-pendants/ep-open-heart-18k-rose-gold-necklaces-pendants-1414158765.html)
  - [Return to Tiffany Love Lock Necklace](https://www.tiffany.com/jewelry/necklaces-pendants/return-to-tiffany-sterling-silver-necklaces-pendants-1155173575.html)
  - [Tiffany Knot Pendant](https://www.tiffany.com/jewelry/necklaces-pendants/tiffany-knot-pendant-68887224/)

---

## Slide 11 - Demo

### Headline

**Demo case: one bridal memory, two Tiffany-ready drafts**

### On-slide content

### Final slide-ready version

**Client**

- **Sun Ruoning**
- Gold; bridal stage; wants simple bands for daily wear; no flashy diamonds

**Logic**

- **Memory**: daily-wear bridal rings
- **Trend cue**: pearl and silver layering
- **Angle**: soft bridal styling conversation

**Draft 1**
“孙小姐，前几天整理日常佩戴的戒圈时，又想到您之前说想看低调一点、婚后也能常戴的款式。我这边挑了几组比较克制的 Tiffany 戒圈和叠戴思路，如果您方便，我稍后发您两三张对比图。”
**English**:  
“Sun, I was looking through a few everyday ring options recently and thought again about what you said before, that you wanted something understated and easy to keep wearing after the wedding. I picked out a few Tiffany ring and layering directions that feel more restrained. If convenient, I can send you two or three comparison images a little later.”

**Draft 2**
“想到您之前提过，希望婚后也还是能日常戴，所以我另外留了一个更轻一点的方向：干净的戒圈配一条很细的珍珠项链，不会太正式。您如果愿意，我可以把更简洁和稍微有层次感的两种搭配一起发您。”
**English**:  
“I also remembered you mentioned wanting something you could keep wearing easily after the wedding, so I saved a lighter direction as well: a clean band with a very delicate pearl necklace, so it doesn’t feel too formal. If you’d like, I can send both versions, one simpler and one with a little more layering.”

**Recommended Tiffany pieces**

- Tiffany Forever Wedding Band Ring in Platinum, 4.5 mm Wide
- Elsa Peretti Pearls by the Yard Necklace
- Tiffany 1837 Ring in Silver, Narrow

**Bottom caption**
One memory can expand into two message options and three concrete Tiffany directions.

### Visual recommendation

- Left: client profile + logic
- Right: two draft boxes
- Bottom: 3 product chips

### Screenshot suggestion

Use the `BENCH_007` raw-output block or log view from `module_5/run_log.json`.

### Source alignment

- Client memory: `module_5/benchmark/benchmark_clients.json`
- Original generated case: `module_5/run_log.json`
- Product / output schema: `module_5/system-prompt v2.md`
- Tiffany product references:
  - [Tiffany Forever Wedding Band Ring](https://www.tiffany.com/jewelry/rings/tiffany-forever-wedding-band-ring-GRP00370/)
  - [Elsa Peretti Pearls by the Yard Necklace](https://www.tiffany.com/jewelry/necklaces-pendants/ep-pearl-by-the-yard-sterling-silver-freshwater-pearl-necklaces-pendants-1593441730.html)
  - [Tiffany 1837 Ring in Silver, Narrow](https://www.tiffany.com/jewelry/rings/tiffany-1837-sterling-silver-rings-1152144421.html)

### Working note

For `BENCH_007`, the **raw** generated payload preserves the bridal-jewelry scenario clearly, while the parsed section in `run_log.json` appears to contain a mismatched sneaker draft. For the slide, use the bridal memory + raw message + Tiffany remapping above.

---

## Slide 12 - Test Design

### Headline

**We tested outputs with both automated audit and human review**

### On-slide content

**Automated evaluation flow**
Results -> Evaluation Agent -> Rubric -> Report -> Refine Feedback -> Outreach Agent

**Rubric**

- Groundedness
- Over-promotion
- Would a CA send it?
- 1-5 score per dimension

**Human review**

- usefulness
- trust
- brand fit
- final editability

**Sample**

- 20 benchmark cases
- 1 batch evaluation
- March 30, 2026

### Layout note

Top half = flow  
Bottom half = two compact cards:

- Automated evaluation
- Human review

### Source alignment

- Evaluation workflow: `module_5/eval_agent.py`
- Rubric definitions and sample size: `module_5/EVAL_REPORT.md`
- WeChat / CA behavior constraints: `module_5/system-prompt v2.md`

---

## Slide 13 - Next Steps

### Headline

**The path from MVP to product is real data plus real workflow**

### On-slide content

**1. Live product data**

- connect to official catalog / website data
- replace simulated product knowledge

**2. CRM integration**

- connect to real CRM
- match the new system with real client profiles and interaction history

**3. CA approval workflow**

- review before send
- edit before send
- keep the CA in control of the final message

**Bottom line**
Move from a strong MVP to a real clienteling copilot.

---



