import forge.GuiDesktop;
import forge.card.CardAiHints;
import forge.gui.GuiBase;
import forge.item.PaperCard;
import forge.model.FModel;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.HashSet;
import java.util.TreeMap;

/** Export the installed rules database. Arguments: output.tsv and comma-separated edition codes. */
public class ExportCardIndex {
    public static void main(String[] args) throws Exception {
        GuiBase.setInterface(new GuiDesktop());
        FModel.initialize(null, null);
        var editions = new HashSet<>(Arrays.asList(args[1].split(",")));
        var cards = new TreeMap<String, PaperCard>();
        var database = FModel.getMagicDb().getCommonCards();
        for (var card : database.getUniqueCards()) cards.put(card.getName(), card);
        for (var card : database.getAllCards()) {
            if (editions.contains(card.getEdition()) && card.getArtIndex() == 1) cards.put(card.getName(), card);
        }
        try (var out = new PrintWriter(args[0], "UTF-8")) {
            for (var card : cards.values()) {
                var rules = card.getRules();
                out.println(String.join("\t",card.getName(), card.getEdition(), card.getRarity().toString(),
                    Byte.toString(rules.getColorIdentity().getColor()), Integer.toString(rules.getManaCost().getCMC()),
                    rules.getType().toString(), Boolean.toString(CardAiHints.isRemovedFromAiDecks(rules)),
                    Boolean.toString(rules.canBeCommander()), rules.getOracleText().replaceAll("\\s+", " ")));
            }
        }
        System.exit(0);
    }
}
