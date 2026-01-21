### Online traces

As people spend more time online, the traces they leave behind can collectively shape a surprisingly detailed picture of who they are. A familiar example is ["Google knows everything about you
."](https://www.reddit.com/r/google/comments/52k2ur/this_is_scaring_me_google_knows_everything_about/)

What’s changing now is the interface through which people access the internet. We don’t only rely on search engines anymore, we increasingly use LLM chatbots as a first stop. And unlike search, chatbot use is inherently conversational. A prompt isn’t just a keyword, it’s a piece of language shaped by personality, context, and intent.

A recent the viral prompt asking ChatGPT to ["create image of you based on how i treated you"](https://www.thedailyjagran.com/technology/are-you-treating-your-chatgpt-right-social-media-reacts-to-chatgpt-image-of-how-its-being-treated-10293280) shows this point. Many users felt the output reflected something real about their interaction patterns. Because conversations contain richer signals: writing style, recurring topics, tone, and sometimes emotional cues.

As LLMs become a default interface for everyday thinking and browsing, a "personal LLM" (an agent trained or conditioned on your history and preferences) can accumulate a deeper behavioral trace than traditional search ever did.

### The disclosure paradox in relationships

People often hesitate to disclose information when disclosure could weaken their position. The [NDAI](https://arxiv.org/pdf/2502.07924) paper frames this tension clearly: revealing what you want can help you reach agreement faster, but it can also be used against you.

Few settings make this more visceral than relationships. Choosing a partner,romantic, friendship, or co-founder, is a negotiation over values, needs, and boundaries. And modern life amplifies the stakes: opportunities and options abound, which makes it feel riskier to say the wrong thing too early.

So we live in a constant tension: Reveal enough to test compatibility and build trust. Hold back enough to avoid losing the opportunity altogether. In practice, people rarely disclose their full preferences upfront. Instead, we reveal small hints over time as the relationship progresses, while keeping the most sensitive parts of our identity private.


### Introducing "Untitled"

Putting these together here are observations:
1. LLM conversations create rich online traces that can reflect who we are.
2. Relationships are technically a disclosure paradox. We need honesty to find alignment, but honesty can be costly. 

"Untitled"'s core idea is straightforward. If two people want to understand their compatibility and they cannot ask sensitive questions directly, then what if each person’s "personal LLM" can answer on their behalf, without exposing the underlying questions or private context to the other person.

To make this safe, "Untitled" follows the setting proposed in NDAI. Negotiation is conducted by AI agents inside a Trusted Execution Environment (TEE). The TEE acts like a sealed room where agents can compute over sensitive information, but neither party (and no operator) can see the private inputs during execution.

The result is a compatibility score (and potentially a structured summary), reflecting where two people align and where they might clash, without forcing either person to reveal their most sensitive preferences prematurely.

<!-- Human hesitate to disclosure something given there is risk of disclosure would threaten position. [NDAI](https://arxiv.org/pdf/2502.07924) paper has good explanation on this. 

One of the fundamental negotiation which been passed since the start of humanity is relationship. Chosing the right partner requires negotiation, and especially modern times where information and opportunities overflood to just commit to person lives near us, the disclosure paradox here is so real. We are always on weird tension of "try to reveal ownself as much to see compatibility" vs "try not to reveal self much cus scared of messing opportunity to get closer". Our full history and identity and thoughts, we keep them under secret while slowly disclosing small hints/information as the deal progresses.  -->

<!-- ### Blind

ok what we learnt? 1) online trace leaves on LLM knows alot about ourself 2) relationship(i'm not limiting only dating context. could be friend or finding work partner etc) embeds the disclosure paradox. 

By combining, we could think of interesting solution that what if instead of us human to make a negotiation, let our personal LLM who has enough information about us to perform this onbehalf? [NDAI](https://arxiv.org/pdf/2502.07924) paper suggested a setting where negotiations are conducted by AI agents on behalf of two parties inside a Trusted Execution Environment (TEE), as an solution for disclosure paradox. By extend this, we developed `Blind`.

Blind's core idea is, if two people wants to know each other, instead of asking sensitive questions directly, ask each other's personal LLM. And as we also want to hide the questions, inside a TEE agent could perform question/answer onbehalf of users. And finally agent returns how the other people have similar expectation to each other. And we called this "compatibility score". -->