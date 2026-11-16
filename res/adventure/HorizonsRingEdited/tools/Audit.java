import forge.GuiDesktop;
import forge.gui.GuiBase;
import forge.item.*;
import forge.model.FModel;
import forge.deck.io.DeckSerializer;
import java.nio.file.*;
import java.util.*;

public class Audit {
    public static void main(String[] args) throws Exception {
        GuiBase.setInterface(new GuiDesktop());
        FModel.initialize(null,null);
        var db = FModel.getMagicDb();
        for (String code : List.of("MH1","MH2","LTR")) {
            var names = new TreeMap<String,String>();
            var basics = new TreeSet<String>();
            for (var card : db.getCommonCards().getAllCards()) if (card.getEdition().equals(code)) {
                if(card.getArtIndex()==1) names.put(card.getName(),card.getRarity().toString());
                if (card.getRules().getType().isBasicLand()) basics.add(card.getName());
            }
            var counts = new TreeMap<String,Integer>();
            names.values().forEach(r -> counts.merge(r,1,Integer::sum));
            System.out.println("AUDIT " + code + " " + names.size()+" "+counts+" "+basics+" digital="+names.keySet().stream().filter(n->n.startsWith("A-")).toList());
            var ed = db.getEditions().get(code);
            var prints = new TreeMap<String,Integer>();
            for(int i=0;i<100;i++) for(var pc:BoosterPack.fromSet(ed).getCards()) prints.merge(pc.getEdition(),1,Integer::sum);
            System.out.println("AUDIT packs "+code+" "+prints);
            for(String key: db.getSpecialBoosters().getItemNames()) if(key.startsWith(code+" ")) {
                var pack=forge.item.generation.BoosterGenerator.getBoosterPack(db.getSpecialBoosters().get(key));
                System.out.println("AUDIT "+key+" "+pack.size()+" "+pack.stream().map(PaperCard::getEdition).distinct().toList());
            }
        }
        var file=Path.of("name-only.dck");
        Files.writeString(file,"[metadata]\nName=Audit\n[Main]\n1 Plains\n1 Counterspell\n1 Forest\n");
        for(var pc:DeckSerializer.fromFile(file.toFile()).getMain().toFlatList()) System.out.println("AUDIT name-only "+pc.getName()+"|"+pc.getEdition());
        System.exit(0);
    }
}
