import forge.GuiDesktop;
import forge.adventure.data.*;
import forge.adventure.util.*;
import forge.deck.Deck;
import forge.gui.GuiBase;
import forge.item.PaperCard;
import forge.localinstance.properties.ForgeConstants;
import forge.model.FModel;
import java.nio.file.*;
import java.util.*;

public class VerifyPlane {
    static final Set<String> editions = new HashSet<>();
    static final Set<String> checked = new HashSet<>();
    static int samples;
    static int deckRewardChecks;
    static void check(boolean ok,String why) { if (!ok) throw new AssertionError(why); }
    static void card(PaperCard c,String source) {
        check(c!=null && editions.contains(c.getEdition()),source+" -> "+c+" "+(c==null?"":c.getEdition()));
        samples++;
    }
    static void deck(Deck d,String source) {
        check(d!=null && d.getMain().countAll()>0,"Empty "+source);
        for(var c:d.getAllCardsInASinglePool().toFlatList()) card(c,source);
    }
    static void verifyFile(String ref) throws Exception {
        if(!checked.add(ref))return;
        var file=Config.instance().getFile(ref);
        check(file!=null && file.path().contains("/AvatarEdited/"),"Reference "+ref);
        var result=CardUtil.getDeck(ref,true,false,"",false,false);
        deck(result,ref);
        check(result.getMain().countAll()>=40,ref+" is short");
        var expected=new TreeMap<String,Integer>();
        for(String row:Files.readAllLines(file.file().toPath())) if(row.matches("[0-9]+ .*")) {
            String[] parts=row.split(" ",2);expected.merge(parts[1],Integer.parseInt(parts[0]),Integer::sum);
        }
        var actual=new TreeMap<String,Integer>();
        for(var c:result.getAllCardsInASinglePool().toFlatList())actual.merge(c.getName()+"|"+c.getEdition()+"|"+c.getArtIndex(),1,Integer::sum);
        check(expected.equals(actual),"Serialization mismatch "+ref);
    }
    static void enemy(EnemyData e) throws Exception {
        for(String ref:e.deck) {
            boolean firstVisit=!checked.contains(ref);
            verifyFile(ref);
            if(firstVisit && e.rewards!=null) {
                var cards=CardUtil.getDeck(ref,true,false,"",false,false).getMain().toFlatList();
                for(var rule:e.rewards){
                    String type=rule.type==null?"card":rule.type;
                    if(rule.cardName!=null || !Set.of("card","randomCard","deckCard").contains(type))continue;
                    var pool=type.equals("deckCard")?cards:RewardData.getAllCards();
                    check(!CardUtil.getPredicateResult(pool,rule).isEmpty(),"Empty enemy reward "+e.name+" "+ref);
                    if (type.equals("deckCard")) {
                        var guaranteed = new RewardData(rule);
                        guaranteed.probability = 1;
                        var prizes = guaranteed.generate(false, cards, false);
                        check(prizes.size > 0, "Empty deck trophy " + ref);
                        for (var prize : prizes) card(prize.getCard(), ref + " trophy");
                        deckRewardChecks++;
                    }
                }
            }
        }
        var d=e.generateDeck(false,false);deck(d,e.name);
        if(e.rewards!=null)for(var r:e.rewards)for(var prize:r.generate(false,d.getMain().toFlatList(),false)) {
            if(prize.getCard()!=null)card(prize.getCard(),e.name);
            if(prize.getDeck()!=null)deck(prize.getDeck(),e.name);
        }
        if(e.nextEnemy!=null)enemy(e.nextEnemy);
    }
    public static void main(String[] args) throws Exception {
        TestProfile.require();
        GuiBase.setInterface(new GuiDesktop());FModel.initialize(null,null);
        Path settings=Path.of(ForgeConstants.USER_ADVENTURE_DIR,"settings.json").toAbsolutePath().normalize();
        check(settings.startsWith(Path.of("").toAbsolutePath()),"Use a separate disposable profile");
        Files.createDirectories(settings.getParent());Files.writeString(settings,"{\"plane\":\"AvatarEdited\"}");
        var config=Config.instance();
        config.getSettingData().useAllCardVariants=args.length>1 && Boolean.parseBoolean(args[1]);
        var cfg=config.getConfigData();editions.addAll(Arrays.asList(cfg.allowedEditions));
        AdventureOverrides.instance().load(config.getPrefix(),FModel.getMagicDb().getEditions(),cfg);
        for (var candidate : RewardData.getAllCards()) card(candidate, "complete Adventure reward pool");
        for(var diff:cfg.difficulties) {
            Current.player().updateDifficulty(diff);
            for(var e:WorldData.getAllEnemies())enemy(e);
            System.out.println("VERIFIED "+diff.name+" "+WorldData.getAllEnemies().size+" enemies; "+checked.size()+" files");
        }
        var mappings=Files.readAllLines(config.getFile("tools/enemy-mapping.tsv").file().toPath());
        for(String row:mappings.subList(1,mappings.size()))verifyFile(row.split("\t")[2]);
        System.out.println("VERIFIED ALL DECK FILES "+checked.size()+"; deck reward checks="+deckRewardChecks);
        var storeFailures=new ArrayList<String>();
        for(var shop:WorldData.getShopList()) {
            if(shop.name.startsWith("AvatarTown") && shop.rewards.size==4) {
                var reserved=new HashSet<String>();
                for(int i=0;i<3;i++)for(var choice:shop.rewards.get(i).cardUnion){
                    var entry=choice.cardName.split("\\|");
                    var pc=CardUtil.getCardByNameAndEdition(entry[0],entry[1]);
                    check(pc.getRarity().toString().equals(i==0?"C":"U") && reserved.add(pc.getName()),shop.name+" "+pc);
                }
                var draw=shop.rewards.get(3);
                var pool=CardUtil.getDeck(draw.sourceDeck,false,false,"",false,false).getMain().toFlatList();
                var weights=new HashMap<String,Integer>();
                for(var pc:CardUtil.getPredicateResult(pool,draw)){
                    card(pc,shop.name);
                    check(!reserved.contains(pc.getName()),shop.name+" duplicate "+pc);
                    weights.merge(pc.getRarity().toString(),1,Integer::sum);
                }
                check(weights.equals(Map.of("C",30,"U",50,"R",18,"M",2)),shop.name+" "+weights);
            }
            int count=0;boolean cardsOnly=true;
            for(var r:shop.rewards) {
                if(r.type!=null && !Set.of("card","randomCard","Union","cardPackShop").contains(r.type))cardsOnly=false;
                var stock=r.generate(false,false);
                if(r.probability==0 || r.probability>=1) {
                    if(r.type==null || Set.of("card","randomCard","Union","cardPackShop").contains(r.type))
                        check(stock.size>0,"Empty shop rule "+shop.name+" "+new com.badlogic.gdx.utils.Json().toJson(r));
                }
                for(var prize:stock){
                    count++;
                    if(prize.getCard()!=null)card(prize.getCard(),shop.name);
                    if(prize.getDeck()!=null)deck(prize.getDeck(),shop.name);
                }
            }
            if(count==0&&cardsOnly)storeFailures.add(shop.name);
        }
        check(storeFailures.isEmpty(),"Empty shops "+storeFailures);
        var database=FModel.getMagicDb().getEditions();
        var draftSets=Arrays.stream(cfg.allowedEvents).map(database::get).toList();
        var valid=AdventureEventData.getValidDraftBlocks(draftSets).stream().map(b->b.getName()).collect(java.util.stream.Collectors.toSet());
        var intended=Arrays.stream(cfg.allowedEvents).map(code->"Avatar "+code).collect(java.util.stream.Collectors.toSet());
        check(valid.equals(intended),"Unexpected draft blocks "+valid);
        if(args.length>0) {
            int lootRules=0;
            var emptyLoot = new ArrayList<String>();
            for(String line:Files.readAllLines(Path.of(args[0]))) {
                var pair=line.split("\t",2);
                var rule=new com.badlogic.gdx.utils.Json().fromJson(RewardData.class,pair[1]);
                rule.probability=1;
                var rewards=rule.generate(false,false);
                if (rewards.size == 0) emptyLoot.add(line);
                for(var reward:rewards) {
                    if(reward.getCard()!=null)card(reward.getCard(),pair[0]);
                    if(reward.getDeck()!=null)deck(reward.getDeck(),pair[0]);
                }
                lootRules++;
            }
            check(emptyLoot.isEmpty(), "Empty loot rules: " + String.join("\n", emptyLoot));
            System.out.println("VERIFIED LOOT RULES "+lootRules);
        }
        var ctor=Class.forName("forge.adventure.scene.AdventureDeckEditor$AdventureEditorConfig").getDeclaredConstructor();
        ctor.setAccessible(true);
        var editor=ctor.newInstance();
        var books=ItemListData.getSketchBooks();
        for(var book:books)Current.player().getItems().add(book);
        var landMethod=editor.getClass().getMethod("getBasicLandSets",Deck.class);
        landMethod.setAccessible(true);
        var landSets=new HashSet<String>();
        for(Object ed:(List<?>)landMethod.invoke(editor,new Deck()))landSets.add(((forge.card.CardEdition)ed).getCode());
        check(landSets.equals(new HashSet<>(Arrays.asList(cfg.allowedEvents))),"Sketchbook lands "+landSets);
        System.out.println("VERIFIED SKETCHBOOKS "+books.size+" land editions="+landSets);
        for(String code:cfg.allowedEvents){
            for(int i=0;i<16;i++){
                deck(AdventureEventController.instance().generateBooster(code),code+" shop booster");
                var block=AdventureOverrides.instance().getBlock("Avatar "+code);
                for(var c:block.getBooster(code).get())card(c,code+" event booster");
            }
        }
        var sealed=new AdventureEventData(247L,AdventureEventController.EventFormat.Sealed);
        check(sealed.getCardBlock()!=null,"No sealed event");
        var participantCtor=AdventureEventData.AdventureEventParticipant.class.getDeclaredConstructor();
        participantCtor.setAccessible(true);
        sealed.participants=new AdventureEventData.AdventureEventParticipant[]{participantCtor.newInstance()};
        sealed.generateSealedPool();
        for(var c:sealed.rewardDeck.getAllCardsInASinglePool().toFlatList())card(c,"sealed pool");
        check(sealed.rewardDeck.getAllCardsInASinglePool().countAll()==84,"sealed pool size");
        for(var participant:sealed.participants)if(!(participant instanceof AdventureEventData.AdventureEventHuman))
            deck(participant.getDeck(),"sealed opponent");
        var draftEvent=new AdventureEventData(247L,AdventureEventController.EventFormat.Draft);
        draftEvent.participants=new AdventureEventData.AdventureEventParticipant[8];
        var enemyName=AdventureEventData.AdventureEventParticipant.class.getDeclaredField("enemyDataName");
        enemyName.setAccessible(true);
        for(int i=0;i<8;i++){
            draftEvent.participants[i]=participantCtor.newInstance();
            enemyName.set(draftEvent.participants[i],WorldData.getAllEnemies().get(i).name);
        }
        for (var event : List.of(sealed, draftEvent)) {
            int packs = 0;
            for (var tier : event.rewards) {
                if (tier == null || tier.cardRewards == null) continue;
                for (var prize : tier.cardRewards) {
                    deck(prize, event.format + " prize for " + tier.minWins + " wins");
                    packs++;
                }
            }
            check(packs > 0, event.format + " missing prize boosters");
        }
        var draft=draftEvent.getDraft();
        int picks=0;
        while(draft.hasNextChoice()){
            var options=draft.nextChoice().toFlatList();
            for(var c:options)card(c,"draft pick");
            draft.setChoice(options.get(0),forge.deck.DeckSection.Sideboard);
            check(++picks<=42,"draft loop");
        }
        check(picks==42,"draft picks "+picks);
        for(var d:draft.getComputerDecks())deck(d,"draft opponent");
        check(new AdventureEventData(247L,AdventureEventController.EventFormat.Jumpstart).cardBlock==null,
            "Unsafe native Jumpstart block");
        System.out.println("VERIFIED sealed pool and opponents, draft picks="+picks);
        for(String name:cfg.allowedJumpstart){
            var block=AdventureOverrides.instance().getBlock(name);
            var packs=AdventureEventController.instance().getJumpstartBoosters(block,6);
            check(!packs.isEmpty(),name);
            for(var d:packs)deck(d,name);
        }
        System.out.println("PASS card instances="+samples+" shops="+WorldData.getShopList().size);
        System.exit(0);
    }
}
