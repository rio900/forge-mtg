package forge.adventure.util;

import forge.adventure.data.DifficultyData;
import forge.card.ColorSet;
import forge.deck.Deck;
import forge.util.MyRandom;
import java.util.Set;

public final class AvatarStarters {
    public static boolean handles(Config cfg, AdventureModes mode) {
        return "AvatarEdited".equals(cfg.getPlane()) && (mode == AdventureModes.Chaos || mode == AdventureModes.Pile);
    }

    public static Deck generate(Config cfg, ColorSet color, DifficultyData difficulty, AdventureModes mode) {
        var paths = difficulty.pileDecks;
        if (paths == null || paths.size != 5)
            throw new IllegalStateException("Missing AvatarEdited Pile templates for " + difficulty.name);
        String key = null;
        if (mode == AdventureModes.Chaos) {
            key = String.valueOf("WUBRG".charAt(MyRandom.getRandom().nextInt(5)));
        } else {
            for (String candidate : paths.keys())
                if (ColorSet.fromNames(candidate.toCharArray()).equals(color)) key = candidate;
        }
        String path = key == null ? null : paths.get(key);
        if (path == null || !path.equals("decks/starter/pile-" + difficulty.name + "-" + key + ".json")
                || !cfg.getFile(path).exists() || !cfg.getFile(path).path().contains("/AvatarEdited/"))
            throw new IllegalStateException("Missing local AvatarEdited template " + difficulty.name + "/" + key + ": " + path);
        var deck = CardUtil.getDeck(path, false, false, "", false, false);
        validate(path, deck, Set.of(cfg.getConfigData().allowedEditions));
        if (!deck.getName().equals("Avatar Pile " + difficulty.name + " " + key))
            throw new IllegalStateException(path + ": unexpected generated deck " + deck.getName());
        return deck;
    }

    public static void validate(String path, Deck deck, Set<String> editions) {
        if (deck == null) throw new IllegalStateException(path + ": no deck");
        var cards = deck.getAllCardsInASinglePool();
        for (var row : cards) {
            var card = row.getKey();
            if (!editions.contains(card.getEdition()))
                throw new IllegalStateException(path + ": " + row.getValue() + " " + card.getName() + "|" + card.getEdition());
        }
        if (deck.getMain().countAll() != 60 || cards.countAll() != 60)
            throw new IllegalStateException(path + ": expected 60 main cards, found " + deck.getMain().countAll() + " main, " + cards.countAll() + " total");
    }
}
