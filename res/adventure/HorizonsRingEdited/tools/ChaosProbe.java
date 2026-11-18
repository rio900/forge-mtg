import forge.adventure.util.*;
import forge.gui.GuiBase;
import forge.model.FModel;
import java.util.*;

public class ChaosProbe {
    public static void main(String[] args)throws Exception{
        GuiBase.setInterface(new forge.GuiDesktop());FModel.initialize(null,null);
        var cfg=Config.instance();
        if(!cfg.getPlane().equals("HorizonsRingEdited"))throw new AssertionError(cfg.getPlane());
        var allowed=Set.of("MH1","MH2","LTR","MH3","2XM");
        int starts=0;
        for (boolean variants : new boolean[]{false,true}) {
            cfg.getSettingData().useAllCardVariants=variants;
            for (var difficulty : cfg.getConfigData().difficulties) {
                Current.player().updateDifficulty(difficulty);
                for (int attempt=0;attempt<10;attempt++) {
                    var deck=cfg.starterDeck(forge.card.ColorSet.fromNames("White"),difficulty,
                            AdventureModes.Chaos,0,FModel.getMagicDb().getEditions().get("MH1"));
                    if (deck.getMain().countAll()!=60) throw new AssertionError(deck.getName());
                    for (var card : deck.getAllCardsInASinglePool().toFlatList()) {
                        if (!allowed.contains(card.getEdition())) throw new AssertionError(card+"|"+card.getEdition());
                    }
                    starts++;
                }
            }
        }
        System.out.println("CHAOS verified "+starts+" starts of 60 cards, outside=0");
        var dir=java.nio.file.Path.of(forge.localinstance.properties.ForgeConstants.CUSTOM_STARTER_DECK_DIR).toAbsolutePath().normalize();
        if(!dir.startsWith(java.nio.file.Path.of("").toRealPath()))throw new AssertionError(dir);
        var control=new forge.deck.Deck("Printing control");
        control.getMain().add("Plains|LTR|1",39);
        control.getMain().add("Counterspell|ICE|1",1);
        FModel.getDecks().getCustomStarterDecks().add(control);
        var catalog=forge.deck.DeckProxy.getAllCustomStarterDecks();
        int index=java.util.stream.IntStream.range(0,catalog.size()).filter(i->catalog.get(i).getName().equals(control.getName())).findFirst().orElseThrow();
        var custom=cfg.starterDeck(forge.card.ColorSet.fromNames("White"),cfg.getConfigData().difficulties[0],
                AdventureModes.Custom,index,FModel.getMagicDb().getEditions().get("LTR"));
        var outside=custom.getMain().toFlatList().stream().filter(c->!allowed.contains(c.getEdition())).toList();
        if(outside.size()!=1 || !outside.get(0).getEdition().equals("ICE"))throw new AssertionError(outside);
        System.out.println("CUSTOM imported "+outside.get(0).getName()+"|"+outside.get(0).getEdition());
        VerifyPlane.editions.addAll(allowed);
        boolean rejected=false;
        try { VerifyPlane.deck(custom,"Custom negative control"); }
        catch(AssertionError expected){rejected=expected.getMessage().contains("ICE");}
        if(!rejected)throw new AssertionError("foreign printing passed verification");
        System.out.println("NEGATIVE CONTROL rejected ICE");
        System.exit(0);
    }
}
