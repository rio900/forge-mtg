import forge.adventure.data.*;
import forge.adventure.util.*;
import forge.gui.GuiBase;
import forge.model.FModel;
import forge.deck.DeckSection;
import java.util.*;

public class Events {
    public static void main(String[] args)throws Exception{
        GuiBase.setInterface(new forge.GuiDesktop());FModel.initialize(null,null);
        var cfg=Config.instance();
        VerifyPlane.check(cfg.getPlane().equals("HorizonsRingEdited"),cfg.getPlane());
        VerifyPlane.editions.addAll(Set.of("MH1","MH2","LTR","MH3","2XM"));
        AdventureOverrides.instance().load(cfg.getPrefix(),FModel.getMagicDb().getEditions(),cfg.getConfigData());
        Current.player().updateDifficulty(cfg.getConfigData().difficulties[0]);
        for(var code:args.length==0?List.of("MH1","MH2","LTR","MH3","2XM"):Arrays.asList(args)){
            var block=AdventureOverrides.instance().getBlock("Horizons "+code);
            var sealed=new AdventureEventData(123L,AdventureEventController.EventFormat.Sealed,block);
            // Headless participants have no portrait. Forge builds their decks normally.
            var ctor=AdventureEventData.AdventureEventParticipant.class.getDeclaredConstructor();
            ctor.setAccessible(true);
            sealed.participants=new AdventureEventData.AdventureEventParticipant[7];
            for(int i=0;i<sealed.participants.length;i++)sealed.participants[i]=ctor.newInstance();
            sealed.generateSealedPool();
            VerifyPlane.deck(sealed.rewardDeck,code+" sealed reward");
            for(var player:sealed.participants)if(!(player instanceof AdventureEventData.AdventureEventHuman))
                VerifyPlane.deck(player.getDeck(),code+" sealed opponent");
            for(var pack:sealed.getRewardPacks(3))VerifyPlane.deck(pack,code+" prize pack");
            System.out.println("EVENT sealed "+code);
            var event=new AdventureEventData(271L,AdventureEventController.EventFormat.Draft,block);
            event.participants=Arrays.copyOf(sealed.participants,8);
            var draft=event.getDraft();
            int picks=0;
            while(draft.hasNextChoice()){
                var choice=draft.nextChoice().toFlatList();
                for(var card:choice)VerifyPlane.card(card,code+" draft pack");
                draft.setChoice(choice.get(0),DeckSection.Sideboard);
                VerifyPlane.check(++picks<=100,"draft loop");
            }
            for(var deck:draft.getComputerDecks())VerifyPlane.deck(deck,code+" draft opponent");
            System.out.println("EVENT draft "+code+" picks="+picks);
        }
        System.exit(0);
    }
}
