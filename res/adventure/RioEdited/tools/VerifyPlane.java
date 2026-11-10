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
        check(file!=null && file.path().contains("/RioEdited/"),"Reference "+ref);
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
        GuiBase.setInterface(new GuiDesktop());FModel.initialize(null,null);
        Path settings=Path.of(ForgeConstants.USER_ADVENTURE_DIR,"settings.json").toAbsolutePath().normalize();
        check(settings.startsWith(Path.of("").toAbsolutePath()),"Use a separate disposable profile");
        Files.createDirectories(settings.getParent());Files.writeString(settings,"{\"plane\":\"RioEdited\"}");
        var config=Config.instance();var cfg=config.getConfigData();editions.addAll(Arrays.asList(cfg.allowedEditions));
        AdventureOverrides.instance().load(config.getPrefix(),FModel.getMagicDb().getEditions(),cfg);
        for(var diff:cfg.difficulties) {
            Current.player().updateDifficulty(diff);
            for(var e:WorldData.getAllEnemies())enemy(e);
            System.out.println("VERIFIED "+diff.name+" "+WorldData.getAllEnemies().size+" enemies; "+checked.size()+" files");
        }
        var mappings=Files.readAllLines(config.getFile("tools/enemy-mapping.tsv").file().toPath());
        for(String row:mappings.subList(1,mappings.size()))verifyFile(row.split("\t")[2]);
        System.out.println("VERIFIED ALL DECK FILES "+checked.size());
        var storeFailures=new ArrayList<String>();
        for(var shop:WorldData.getShopList()) {
            int count=0;boolean cardsOnly=true;
            for(var r:shop.rewards) {
                if(r.type!=null && !Set.of("card","randomCard","Union","cardPackShop").contains(r.type))cardsOnly=false;
                for(var prize:r.generate(false,false)){
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
        var intended=Arrays.stream(cfg.allowedEvents).map(code->"Rio "+code).collect(java.util.stream.Collectors.toSet());
        check(valid.equals(intended),"Unexpected draft blocks "+valid);
        if(args.length>0) {
            int lootRules=0;
            for(String line:Files.readAllLines(Path.of(args[0]))) {
                var pair=line.split("\t",2);
                var rule=new com.badlogic.gdx.utils.Json().fromJson(RewardData.class,pair[1]);
                rule.probability=1;
                var rewards=rule.generate(false,false);
                check(rewards.size>0,"Empty loot "+line);
                for(var reward:rewards) {
                    if(reward.getCard()!=null)card(reward.getCard(),pair[0]);
                    if(reward.getDeck()!=null)deck(reward.getDeck(),pair[0]);
                }
                lootRules++;
            }
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
                var block=AdventureOverrides.instance().getBlock("Rio "+code);
                for(var c:block.getBooster(code).get())card(c,code+" event booster");
            }
        }
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
