package forge.adventure.util;

import forge.adventure.data.DifficultyData;
import forge.deck.Deck;
import forge.deck.DeckgenUtil;
import forge.util.MyRandom;
import java.util.Set;

public final class RioChaos {
    public static Deck starter(String colors, boolean forAi, boolean isTheme, boolean useGeneticAI,
                               String[] editions, DifficultyData difficulty) {
        if (!"RioEdited".equals(Config.instance().getPlane())) {
            return DeckgenUtil.getRandomOrPreconOrThemeDeck(colors, forAi, isTheme, useGeneticAI, editions);
        }
        var templates = difficulty.pileDecks.values().toArray();
        String path = templates.get(MyRandom.getRandom().nextInt(templates.size));
        Deck deck = CardUtil.getDeck(path, false, false, "", false, false);
        var allowed = Set.of(editions);
        if (deck.getMain().countAll() != 60 || deck.getAllCardsInASinglePool().toFlatList()
                .stream().anyMatch(card -> !allowed.contains(card.getEdition()))) {
            throw new IllegalStateException("Invalid RioEdited Chaos starter from " + path);
        }
        return deck;
    }
}
