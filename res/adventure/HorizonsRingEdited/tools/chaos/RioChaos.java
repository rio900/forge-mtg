package forge.adventure.util;

import forge.adventure.data.DifficultyData;
import forge.deck.Deck;
import forge.deck.DeckgenUtil;
import forge.util.MyRandom;
import java.util.Set;

// Config.starterDeck in the installed Adventure build calls this entry point for Chaos.
public final class RioChaos {
    public static Deck starter(String colors, boolean forAi, boolean theme, boolean genetic,
                               String[] editions, DifficultyData difficulty) {
        String plane = Config.instance().getPlane();
        if (!plane.equals("HorizonsRingEdited") && !plane.equals("RioEdited")) {
            return DeckgenUtil.getRandomOrPreconOrThemeDeck(colors, forAi, theme, genetic, editions);
        }

        var templates = difficulty.pileDecks.values().toArray();
        String path = templates.get(MyRandom.getRandom().nextInt(templates.size));
        Deck deck = CardUtil.getDeck(path, false, false, "", false, false);
        var allowed = Set.of(editions);
        if (deck.getMain().countAll() != 60 || deck.getAllCardsInASinglePool().toFlatList()
                .stream().anyMatch(card -> !allowed.contains(card.getEdition()))) {
            throw new IllegalStateException("Invalid " + plane + " Chaos starter from " + path);
        }
        return deck;
    }
}
