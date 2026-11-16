import forge.GuiDesktop;
import forge.adventure.data.*;
import forge.adventure.util.*;
import forge.card.ColorSet;
import forge.deck.Deck;
import forge.gui.GuiBase;
import forge.model.FModel;
import java.util.*;

public class AvatarStarterProbe {
    static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) throws Exception {
        TestProfile.require();
        GuiBase.setInterface(new GuiDesktop());
        FModel.initialize(null, null);
        var cfg = Config.instance();
        require(cfg.getPlane().equals("AvatarEdited"), cfg.getPlane());
        var data = cfg.getConfigData();
        var allowed = Set.of(data.allowedEditions);
        var edition = FModel.getMagicDb().getEditions().get(data.defaultBasicLandSet);
        int chaos = 0, piles = 0, slots = 0;
        for (boolean variants : List.of(false, true)) {
            cfg.getSettingData().useAllCardVariants = variants;
            RewardData.invalidateCardPool();
            for (var level : data.difficulties) {
                Current.player().updateDifficulty(level);
                var names = new HashSet<String>();
                for (var entry : level.pileDecks) {
                    String path = entry.value;
                    var template = new com.badlogic.gdx.utils.Json().fromJson(GeneratedDeckData.class, cfg.getFile(path));
                    require(names.add(template.name), path);
                    int size = 0;
                    for (var slot : template.mainDeck) {
                        size += slot.count;
                        if (slot.cardName == null) {
                            require(slot.colors.length > 0 && slot.rarity.length > 0 && slot.manaCosts.length > 0
                                    && Set.of(slot.editions).equals(allowed), path);
                            require(!CardUtil.getPredicateResult(RewardData.getAllCards(),slot).isEmpty(),
                                    path + " empty " + Arrays.toString(slot.colors) + Arrays.toString(slot.manaCosts));
                        } else {
                            String[] print = slot.cardName.split("\\|");
                            require(print.length == 2 && allowed.contains(print[1]), path + " " + slot.cardName);
                            var card = CardUtil.getCardByNameAndEdition(print[0], print[1]);
                            require(card != null && card.getRules().getType().isBasicLand() && card.getEdition().equals(print[1]), path + " " + slot.cardName);
                        }
                        slots++;
                    }
                    require(size == 60, path + " size " + size);
                    var pile = cfg.starterDeck(ColorSet.fromNames(entry.key.toCharArray()),level,AdventureModes.Pile,0,edition);
                    require(pile.getName().equals(template.name), path + " " + pile.getName());
                    AvatarStarters.validate(path, pile, allowed);
                    piles++;
                }
                for (int i = 0; i < 10; i++) {
                    var actual = cfg.starterDeck(ColorSet.fromNames("White"),level,AdventureModes.Chaos,0,edition);
                    require(names.contains(actual.getName()), level.name + " " + actual.getName());
                    AvatarStarters.validate(actual.getName(), actual, allowed);
                    chaos++;
                }
            }
        }
        var invalid = new Deck("Negative control");
        invalid.getMain().add("Forest|TLA|1",59);
        invalid.getMain().add("Forest|MKM|1",1);
        try {
            AvatarStarters.validate("negative-template", invalid, allowed);
            throw new AssertionError("Accepted foreign basic land");
        } catch (IllegalStateException ex) {
            require(ex.getMessage().contains("negative-template") && ex.getMessage().contains("Forest|MKM"), ex.getMessage());
        }
        require(chaos == 80 && piles == 40, "coverage");
        System.out.println("PASS Chaos=" + chaos + " cards=" + chaos*60 + " Pile=" + piles + " cards=" + piles*60 + " slots=" + slots + " foreign=0");
        System.exit(0);
    }
}
