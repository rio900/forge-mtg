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
    static final Map<String,String> modern=new HashMap<>();
    static void loadModern() throws Exception {
        for(String line:Files.readAllLines(Config.instance().getFile("tools/modern-cards.txt").file().toPath())){
            String[] row=line.split("\\|");
            modern.put(row[0]+"|"+row[1],row[2]);
        }
        check(modern.size()==46,"Modern pool");
    }
    static boolean legal(PaperCard c){
        return editions.contains(c.getEdition()) || modern.containsKey(c.getName()+"|"+c.getEdition());
    }
    static int samples;
    static void check(boolean ok,String why) { if (!ok) throw new AssertionError(why); }
    static void card(PaperCard c,String source) {
        boolean special=source.startsWith("RingTown") || source.startsWith("decks/shop/")
                || source.startsWith("decks/arena/") || source.equals("decks/converted/griselbrand-1.dck")
                || source.equals("decks/pilot/liliana.dck") || source.equals("Liliana") || source.equals("Griselbrand");
        check(c!=null && (editions.contains(c.getEdition()) || (special && legal(c))),source+" -> "+c+" "+(c==null?"":c.getEdition()));
        samples++;
    }
    static void deck(Deck d,String source) {
        check(d!=null && d.getMain().countAll()>0,"Empty "+source);
        for(var c:d.getAllCardsInASinglePool().toFlatList()) card(c,source);
    }
    static void verifyFile(String ref) throws Exception {
        if(!checked.add(ref))return;
        var file=Config.instance().getFile(ref);
        check(file!=null && file.path().contains("/HorizonsRingEdited/"),"Reference "+ref);
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
    static void chestCard(PaperCard c,String source) {
        card(c,source);
        check(Set.of("U","R","M").contains(c.getRarity().toString()),"Chest rarity "+source+" "+c);
    }
    static void chestPool(RewardData rule,String source) {
        if(rule.cardUnion!=null) {
            for(var member:rule.cardUnion)chestPool(member,source);
        } else if(rule.cardName!=null) {
            var print=rule.cardName.split("\\|");
            chestCard(CardUtil.getCardByNameAndEdition(print[0],print[1]),source);
        } else {
            for(var pc:CardUtil.getPredicateResult(RewardData.getAllCards(),rule))chestCard(pc,source);
        }
    }
    static void verifySingles(ShopData shop) {
        var localOdds=Map.of("C",30,"U",50,"R",18,"M",2);
        var generalOdds=Map.of("U",80,"R",19,"M",1);
        String color=shop.name.substring("RingTown".length()).replace("Creatures","");
        int mask=Map.of("White",1,"Blue",2,"Black",4,"Red",8,"Green",16,"Colorless",0).get(color);
        check(shop.rewards.size==6,shop.name+" slots");
        var banned=Set.of(Config.instance().getConfigData().restrictedCards);
        var db=FModel.getMagicDb().getCommonCards();
        for(int i=0;i<6;i++){
            var rule=shop.rewards.get(i);
            var odds=i<3?localOdds:generalOdds;
            String source="decks/shop/"+(i<3?color:"GeneralWeighted")+".dck";
            check(rule.count==1 && source.equals(rule.sourceDeck),shop.name+" slot "+i);
            if(i==0 || i==3){
                var deck=CardUtil.getDeck(source,false,false,"",false,false);
                var pool=CardUtil.getPredicateResult(deck.getMain().toFlatList(),rule);
                var expected=new HashSet<String>();
                for(var pc:db.getAllCards()){
                    if(legal(pc) && !banned.contains(pc.getName())
                            && odds.containsKey(pc.getRarity().toString())
                            && (i>=3 || pc.getRules().getColorIdentity().getColor()==mask))
                        expected.add(pc.getName()+"|"+pc.getEdition()+"|"+pc.getRarity());
                }
                var actual=new HashSet<String>();
                var counts=new HashMap<String,Integer>();
                var entries=new HashMap<PaperCard,Integer>();
                for(var pc:pool){
                    card(pc,shop.name);
                    actual.add(pc.getName()+"|"+pc.getEdition()+"|"+pc.getRarity());
                    counts.merge(pc.getRarity().toString(),1,Integer::sum);
                    entries.merge(pc,1,Integer::sum);
                }
                check(actual.equals(expected),source+" pool difference "+expected.stream().filter(n->!actual.contains(n)).toList());
                for(var entry:odds.entrySet())
                    check(100*counts.getOrDefault(entry.getKey(),0)==entry.getValue()*pool.size(),source+" weights "+counts);
                for(var pc:entries.keySet()){
                    var variants=db.getAllCardsNoAlt(pc.getName()).stream().filter(v->pc.getEdition().equals(v.getEdition())).toList();
                    if(variants.stream().anyMatch(v->v.getRarity()!=pc.getRarity()))
                        for(var v:variants)check(entries.get(pc).equals(entries.get(v)),source+" variant weights "+pc);
                }
            }
            for(int draw=0;draw<10;draw++){
                var roll=rule.generate(false,false);
                check(roll.size==1,source+" count");
                var pc=roll.first().getCard();
                card(pc,shop.name);
                check(odds.containsKey(pc.getRarity().toString()) && (i>=3 || pc.getRules().getColorIdentity().getColor()==mask),source+" draw "+pc);
            }
        }
        System.out.println("STOCK "+shop.name+" full pools and all six slot weights verified");
    }
    public static void main(String[] args) throws Exception {
        GuiBase.setInterface(new GuiDesktop());FModel.initialize(null,null);
        Path settings=Path.of(ForgeConstants.USER_ADVENTURE_DIR,"settings.json").toAbsolutePath().normalize();
        check(settings.startsWith(Path.of("").toAbsolutePath()),"Use a separate disposable profile");
        Files.createDirectories(settings.getParent());Files.writeString(settings,"{\"plane\":\"HorizonsRingEdited\"}");
        var config=Config.instance();var cfg=config.getConfigData();editions.addAll(Arrays.asList(cfg.allowedEditions));
        check(editions.equals(Set.of("LTR","MH1","MH2")),"unexpected pool");
        config.getSettingData().useAllCardVariants=args.length<2 || Boolean.parseBoolean(args[1]);
        loadModern();
        AdventureOverrides.instance().load(config.getPrefix(),FModel.getMagicDb().getEditions(),cfg);
        for(var entry:modern.entrySet()){
            var pc=FModel.getMagicDb().getCommonCards().getCard(entry.getKey()+"|1");
            check(pc!=null && pc.getRarity().toString().equals(entry.getValue()),"wrong printing "+entry);
            var draw=CardUtil.generateCards(List.of(pc),new RewardData(),1,new Random(1)).get(0);
            check((draw.getName()+"|"+draw.getEdition()).equals(entry.getKey()),"reward substitution "+entry+" -> "+draw);
        }
        for(var town:Map.of("White",1,"Blue",2,"Black",4,"Red",8,"Green",16).entrySet()){
            var pool=CardUtil.getDeck("decks/arena/"+town.getKey()+".dck",false,false,"",false,false).getMain();
            var cards=pool.toFlatList();
            long local=cards.stream().distinct().filter(c->c.getRules().getColorIdentity().hasAnyColor(town.getValue())).count();
            check(cards.stream().distinct().count()==modern.size() && cards.size()==2*local*modern.size(),"arena pool "+town);
            for(var c:cards.stream().distinct().toList()){
                check(modern.containsKey(c.getName()+"|"+c.getEdition()) &&
                        pool.count(c)==local+(c.getRules().getColorIdentity().hasAnyColor(town.getValue())?modern.size():0),"arena weight "+c);
            }
            String terrain=Map.of("White","plains","Blue","island","Black","swamp","Red","mountain","Green","forest").get(town.getKey());
            var file=config.getFile("maps/map/main_story/"+terrain+"_capital.tmx").file();
            var map=javax.xml.parsers.DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(file);
            var props=map.getElementsByTagName("property");
            String arenaJson=null;
            for(int k=0;k<props.getLength();k++){
                var prop=(org.w3c.dom.Element)props.item(k);
                if(prop.getAttribute("name").equals("arena"))arenaJson=prop.getTextContent();
            }
            var arena=new com.badlogic.gdx.utils.Json().fromJson(ArenaData.class,arenaJson);
            check(arena.rounds==3 && arena.entryFee==100 && arena.rewards[2].length==4,"arena structure "+town);
            var prize=arena.rewards[2][3];
            check(prize.sourceDeck.equals("decks/arena/"+town.getKey()+".dck"),"arena final "+town);
            var generated=prize.generate(false,null,true);
            check(generated.size==1,"one arena prize");
            var reward=generated.first();
            var pc=reward.getCard();
            check(modern.containsKey(pc.getName()+"|"+pc.getEdition()),"wrong arena prize "+pc);
            int before=Current.player().getCards().count(pc);
            Current.player().addReward(reward);
            check(Current.player().getCards().count(pc)==before+1,"arena collection "+pc);
            System.out.println("ARENA "+town.getKey()+" collected "+pc+"|"+pc.getEdition());
        }
        System.out.println("MODERN verified all "+modern.size()+" actual card rolls and five arena pools");
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
            if(shop.name.startsWith("RingTown") && !Set.of("RingTownBooster","RingTownEquipment").contains(shop.name))
                verifySingles(shop);
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
        var intended=Arrays.stream(cfg.allowedEvents).map(code->"Horizons "+code).collect(java.util.stream.Collectors.toSet());
        check(valid.equals(intended),"Unexpected draft blocks "+valid);
        if(args.length>0) {
            int lootRules=0;
            for(String line:Files.readAllLines(Path.of(args[0]))) {
                var pair=line.split("\t",2);
                var rule=new com.badlogic.gdx.utils.Json().fromJson(RewardData.class,pair[1]);
                boolean chest=pair[0].startsWith("chest/");
                if(chest)chestPool(rule,pair[0]);
                rule.probability=1;
                var rewards=rule.generate(false,false);
                check(rewards.size>0,"Empty loot "+line);
                for(var reward:rewards) {
                    if(chest)chestCard(reward.getCard(),pair[0]);
                    else if(reward.getCard()!=null)card(reward.getCard(),rule.sourceDeck!=null && rule.sourceDeck.startsWith("decks/arena/")?rule.sourceDeck:pair[0]);
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
        check(landSets.equals(Set.of("MH2","LTR")),"Sketchbook lands "+landSets);
        System.out.println("VERIFIED SKETCHBOOKS "+books.size+" land editions="+landSets);
        var sheetNames = new HashMap<String,Set<String>>();
        for(String section:List.of("Lands","NewToModern")) {
            var names=new HashSet<String>();
            for(var pc:forge.item.generation.BoosterGenerator.tryGetStaticSheet("MH2 "+section).toFlatList()){
                card(pc,"MH2 "+section);
                names.add(pc.getName());
            }
            sheetNames.put(section,names);
        }
        for(String code:cfg.allowedEvents){
            for(int i=0;i<16;i++){
                var shopPack=AdventureEventController.instance().generateBooster(code);
                deck(shopPack,code+" shop booster");
                var block=AdventureOverrides.instance().getBlock("Horizons "+code);
                var eventPack=block.getBooster(code).get();
                for(var c:eventPack)card(c,code+" event booster");
                for(var pack:List.of(shopPack.getMain().toFlatList(),eventPack)) {
                    check(pack.size()==15 && pack.stream().allMatch(c->code.equals(c.getEdition())),code+" pack composition "+pack);
                    if(code.equals("MH2")){
                        for(var sheet:sheetNames.entrySet())
                            check(pack.stream().anyMatch(c->sheet.getValue().contains(c.getName())),"missing "+sheet.getKey()+" in "+pack);
                    }else check(pack.stream().anyMatch(c->c.getRules().getType().isBasicLand()),code+" no basic land");
                }
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
