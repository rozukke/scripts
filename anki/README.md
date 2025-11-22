# Chinese language learning Anki scripts

> [!NOTE]
> All of these will probably require tweaking and are by no means meant to be generic.

## convert_traditional_chinese.py

Creates a "Tradtional" field for cards with a "Simplified" field.

## generate_examples_llm.py

Uses a local KoboldCPP instance (or equivalent) to generate example sentences that primarily use
words from your deck.

## generate_examples_gemini.py

Same as above, using Gemini API.

## random_tatoeba_examples.py

Upon discovering that LLMs do indeed still suck, I made this script to use a Tatoeba example sentence
set to get the example sentences. Requires `tatoeba_ingest.py --init` to be run.

## tatoeba_ingest.py

Gets latest Tatoeba data and parses it into an SQLite database, exposing the ability to get a random
example sentence for a particular word.
