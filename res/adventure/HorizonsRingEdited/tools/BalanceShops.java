import com.badlogic.gdx.utils.Json;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;
import com.badlogic.gdx.utils.JsonWriter;
import forge.adventure.data.RewardData;
import forge.adventure.util.AdventureOverrides;
import forge.adventure.util.CardUtil;
import forge.adventure.util.Config;
import forge.gui.GuiBase;
import forge.item.PaperCard;
import forge.model.FModel;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Rebuild finite, rarity-weighted specialist stock using Forge's own card predicates. */
public class BalanceShops {
    static final Json json = new Json();
    static final List<String> rarities = List.of("C", "U", "R", "M");
    static List<PaperCard> candidates(RewardData rule) {
        if ("Union".equals(rule.type)) {
            var cards = new LinkedHashSet<PaperCard>();
            for (var member : rule.cardUnion) cards.addAll(candidates(member));
            return new ArrayList<>(cards);
        }
        if (rule.cardName != null) {
            var card = FModel.getMagicDb().getCommonCards().getCard(rule.cardName);
            return card == null ? List.of() : List.of(card);
        }
        return CardUtil.getPredicateResult(RewardData.getAllCards(), rule);
    }
    static String entry(PaperCard card) {
        return card.getName() + "|" + card.getEdition() + "|" + card.getArtIndex();
    }
    static boolean affordable(List<PaperCard> cards) {
        return cards.stream().anyMatch(c -> Set.of("C","U").contains(c.getRarity().toString()));
    }
    static void set(JsonValue object, String key, Object value) {
        object.remove(key);
        object.addChild(key, new JsonReader().parse(json.toJson(value)));
    }
    static String weightedDeck(Path plane, String name, int index, List<PaperCard> cards) throws Exception {
        var groups = new TreeMap<String,List<PaperCard>>();
        for (var c : cards) {
            if (!c.getRules().getType().isBasicLand() && rarities.contains(c.getRarity().toString()))
                groups.computeIfAbsent(c.getName()+"|"+c.getEdition(), k -> new ArrayList<>()).add(c);
        }
        if (groups.isEmpty()) throw new IllegalStateException("Empty specialist "+name);
        var singles = new LinkedHashMap<String,List<PaperCard>>();
        var fixed = new TreeMap<String,Integer>();
        var reserved = new HashMap<String,Integer>();
        for (String rarity : rarities) singles.put(rarity,new ArrayList<>());
        // Edition art can be rerolled by Forge; reserve equal copies of mixed-rarity art.
        for (var group : groups.values()) {
            var first = group.get(0);
            var variants = FModel.getMagicDb().getCommonCards().getAllCardsNoAlt(first.getName()).stream()
                    .filter(c -> c.getEdition().equals(first.getEdition())).toList();
            long distinct = variants.stream().map(PaperCard::getRarity).distinct().count();
            if (distinct == 1) {
                var card = variants.stream().min(Comparator.comparingInt(PaperCard::getArtIndex)).orElseThrow();
                singles.get(card.getRarity().toString()).add(card);
            } else {
                for (var card : variants) {
                    fixed.put(entry(card),1);
                    reserved.merge(card.getRarity().toString(),1,Integer::sum);
                }
            }
        }
        var weights = new LinkedHashMap<String,Integer>();
        var base = Map.of("C",50,"U",40,"R",9,"M",1);
        for (String r : rarities)
            if (!singles.get(r).isEmpty() || reserved.containsKey(r)) weights.put(r,base.get(r));
        String recipient = weights.containsKey("C") ? "C" : weights.containsKey("U") ? "U" :
                weights.containsKey("R") ? "R" : "M";
        weights.merge(recipient,100-weights.values().stream().mapToInt(i->i).sum(),Integer::sum);
        int scale=1;
        for (var w : weights.entrySet())
            scale=Math.max(scale,(singles.get(w.getKey()).size()+reserved.getOrDefault(w.getKey(),0)+w.getValue()-1)/w.getValue());
        // Mixed-rarity variants alone cannot absorb arbitrary extra weight independently.
        for (var w : weights.entrySet()) {
            var pool=singles.get(w.getKey());
            int remaining=w.getValue()*scale-reserved.getOrDefault(w.getKey(),0);
            if(pool.isEmpty()) {
                if(remaining!=0) throw new IllegalStateException("No single-rarity printing for "+name+" "+w.getKey());
                continue;
            }
            int copies=remaining/pool.size(), extra=remaining%pool.size();
            for(int i=0;i<pool.size();i++) fixed.put(entry(pool.get(i)),copies+(i<extra?1:0));
        }
        String ref="decks/shop/specialists/"+name+"-"+index+".dck";
        Path path=plane.resolve(ref);
        Files.createDirectories(path.getParent());
        var text=new StringBuilder("[metadata]\nName="+name+"\n[Main]\n");
        for(var e:fixed.entrySet()) if(e.getValue()>0) text.append(e.getValue()).append(' ').append(e.getKey()).append('\n');
        Files.writeString(path,text.toString());
        return ref;
    }
    public static void main(String[] args) throws Exception {
        GuiBase.setInterface(new forge.GuiDesktop());
        FModel.initialize(null,null);
        var config=Config.instance();
        AdventureOverrides.instance().load(config.getPrefix(),FModel.getMagicDb().getEditions(),config.getConfigData());
        var path=config.getFile("world/shops.json").file().toPath().toAbsolutePath();
        var plane=path.getParent().getParent();
        var shops=new JsonReader().parse(Files.readString(path));
        int changed=0, premium=0;
        for (var shop:shops) {
            String name=shop.getString("name");
            if(name.startsWith("RingTown") || Set.of("Plains","Island","Swamp","Mountain","Forest").contains(name))continue;
            var rules=shop.get("rewards");
            boolean packs=true,cardsOnly=true;
            for(var rule:rules) {
                String type=rule.getString("type","card");
                packs &= type.equals("cardPackShop");
                cardsOnly &= Set.of("card","randomCard","Union").contains(type);
            }
            if(packs) {
                var rule=rules.child;
                set(rule,"count",2);
                rule.remove("addMaxCount");
                var replacement=new JsonValue(JsonValue.ValueType.array);
                rule.next=null;rule.prev=null;
                replacement.addChild(rule);
                shop.remove("rewards");shop.addChild("rewards",replacement);
                set(shop,"unlimited",false);shop.remove("restockPrice");
                continue;
            }
            if(!cardsOnly)continue;
            var pools=new ArrayList<List<PaperCard>>();
            for(var rule:rules) {
                var pool=new ArrayList<>(candidates(json.fromJson(RewardData.class,rule.toJson(JsonWriter.OutputType.json))));
                pool.removeIf(c -> c.getRules().getType().isBasicLand());
                pools.add(pool);
            }
            var fallback=new LinkedHashSet<PaperCard>();
            for(var pool:pools)fallback.addAll(pool);
            if(fallback.isEmpty())throw new IllegalStateException(name+" has no matching cards");
            for(int k=0;k<pools.size();k++)
                if(pools.get(k).isEmpty())pools.set(k,new ArrayList<>(fallback));
            boolean rareOnly=pools.stream().noneMatch(BalanceShops::affordable);
            int remaining=rareOnly?1:4;
            int premiumRemaining=1;
            var replacements=new JsonValue(JsonValue.ValueType.array);
            int i=0;
            for(var rule:rules) {
                if(remaining==0)break;
                boolean premiumRule=!affordable(pools.get(i));
                if(premiumRule && premiumRemaining==0){i++;continue;}
                int count=Math.min(remaining,Math.max(1,rule.getInt("count",1)/2));
                if(premiumRule){count=1;premiumRemaining--;}
                String ref=weightedDeck(plane,name,i,pools.get(i));
                var reward=new JsonValue(JsonValue.ValueType.object);
                set(reward,"type","card");set(reward,"count",count);set(reward,"sourceDeck",ref);
                replacements.addChild(reward);
                remaining-=count;i++;
            }
            shop.remove("rewards");shop.addChild("rewards",replacements);
            set(shop,"unlimited",false);shop.remove("restockPrice");
            changed++;
            if(rareOnly)premium++;
        }
        var references=new HashSet<String>();
        for(var shop:shops) for(var rule:shop.get("rewards"))
            references.add(rule.getString("sourceDeck",""));
        try(var files=Files.list(plane.resolve("decks/shop/specialists"))) {
            for(var file:files.toList())
                if(file.toString().endsWith(".dck") && !references.contains(plane.relativize(file).toString()))
                    Files.delete(file);
        }
        Files.writeString(path,shops.prettyPrint(JsonWriter.OutputType.json,120)+"\n");
        System.out.println("BALANCED "+changed+" specialist shops, "+premium+" premium-only counters");
        System.exit(0);
    }
}
